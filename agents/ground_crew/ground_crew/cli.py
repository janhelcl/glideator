"""CLI for ground crew data management."""

import asyncio
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .agent_runner import CandidateRetrievalAgent
from .db import get_engine
from .io import load_extraction_run
from .sites import format_site_details, get_sites
from .validation import BrowserValidator, ValidationResult, ValidationStatus
from .validation.io import (
    create_validation_run,
    finalize_validation_run,
    fetch_candidates_for_validation,
    get_candidate_by_id,
    record_candidate_validation,
)

app = typer.Typer(help="Ground Crew - Manage extraction run data")
console = Console()

CANDIDATE_EVIDENCE_FIELDS = [
    ("takeoff_landing_areas", "Evidence: takeoff/landing areas"),
    ("rules", "Evidence: rules"),
    ("fees", "Evidence: fees"),
    ("access", "Evidence: access"),
    ("meteostation", "Evidence: meteostation"),
    ("webcams", "Evidence: webcams"),
]

USAGE_STATS_KEYS = [
    "total_prompt_tokens",
    "total_prompt_cost",
    "total_prompt_cached_tokens",
    "total_prompt_cached_cost",
    "total_completion_tokens",
    "total_completion_cost",
    "total_tokens",
    "total_cost",
    "entry_count",
]


def _prompt_iso_timestamp() -> str:
    """Prompt user for an ISO 8601 timestamp string."""
    default_ts = datetime.utcnow().replace(microsecond=0).isoformat()
    while True:
        value = typer.prompt("Extraction timestamp (ISO 8601)", default=default_ts)
        try:
            datetime.fromisoformat(value)
            return value
        except ValueError:
            console.print("[red]Invalid timestamp format. Use YYYY-MM-DDTHH:MM:SS[/red]")


def _prompt_non_empty(message: str) -> str:
    """Prompt until non-empty text is provided."""
    while True:
        value = typer.prompt(message).strip()
        if value:
            return value
        console.print("[red]This field cannot be empty.[/red]")


def _empty_usage_stats() -> Dict[str, Any]:
    """Return a usage stats dict with all fields set to None."""
    stats = {key: None for key in USAGE_STATS_KEYS}
    stats["by_model"] = {}
    return stats


def _collect_candidates() -> List[Dict[str, Any]]:
    """Interactively collect candidate website data."""
    console.print("\n[bold]Candidate websites[/bold]")
    candidates: List[Dict[str, Any]] = []

    while True:
        add_more = typer.confirm(
            "Add a candidate website?" if not candidates else "Add another candidate?",
            default=not candidates,
        )
        if not add_more:
            if candidates:
                return candidates
            console.print("[red]At least one candidate website is required.[/red]")
            continue

        name = _prompt_non_empty("  Name")
        url = _prompt_non_empty("  URL")
        evidence = {
            key: typer.confirm(f"    {label}?", default=False)
            for key, label in CANDIDATE_EVIDENCE_FIELDS
        }

        candidates.append(
            {
                "name": name,
                "url": url,
                "evidence": evidence,
            }
        )

    return candidates


def _prompt_optional_int(message: str) -> Optional[int]:
    """Prompt user for an integer, allowing blank for None."""
    value = typer.prompt(f"{message} (leave blank to skip)", default="").strip()
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        console.print("[red]Please provide a valid integer or leave blank.[/red]")
        return _prompt_optional_int(message)


@app.command()
def load_jsonl(
    file_path: Path = typer.Argument(..., help="Path to JSONL file with extraction runs"),
):
    """Load extraction runs from a JSONL file to the database."""
    if not file_path.exists():
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        raise typer.Exit(1)
    
    engine = get_engine()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    console.print(f"[cyan]Loading {len(lines)} extraction runs from {file_path}[/cyan]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading...", total=len(lines))
        
        loaded_count = 0
        for line in lines:
            data = json.loads(line)
            run_id = load_extraction_run(data, engine)
            loaded_count += 1
            progress.update(task, advance=1, description=f"Loaded run {run_id}")
    
    console.print(f"[green]✓ Successfully loaded {loaded_count} extraction runs![/green]")


@app.command()
def load_single(
    file_path: Path = typer.Argument(..., help="Path to JSON file with single extraction run"),
):
    """Load a single extraction run from a JSON file to the database."""
    if not file_path.exists():
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        raise typer.Exit(1)
    
    engine = get_engine()
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    console.print(f"[cyan]Loading extraction run for site_id={data.get('site_id')}[/cyan]")
    
    run_id = load_extraction_run(data, engine)
    
    console.print(f"[green]✓ Successfully loaded extraction run with run_id={run_id}![/green]")


@app.command("manual-run")
def manual_run():
    """Manually enter run metadata and candidates via the CLI."""
    console.print("[bold cyan]Manual extraction run entry[/bold cyan]\n")
    engine = get_engine()

    site_id = typer.prompt("Site ID", type=int)
    extracted_at = _prompt_iso_timestamp()
    agent = typer.prompt("Agent label", default="Human").strip() or "Human"

    duration_seconds = None
    usage_stats = _empty_usage_stats()
    candidates = _collect_candidates()

    is_successful = typer.confirm("Mark run as successful?", default=True)

    data = {
        "site_id": site_id,
        "extracted_at": extracted_at,
        "duration_seconds": duration_seconds,
        "agent": agent,
        "result": {
            "structured_output": {"candidate_websites": candidates},
            "usage_stats": usage_stats,
            "duration_seconds": duration_seconds,
        },
        "is_successful": is_successful,
    }

    run_id = load_extraction_run(data, engine)
    console.print(
        f"[green]✓ Manual run stored with run_id={run_id} "
        f"({len(candidates)} candidate(s))[/green]"
    )


async def _run_candidate_retrieval_for_sites(
    output_path: Path,
    site_rows,
    engine,
):
    """Run the CandidateRetrievalAgent for the provided site rows."""
    total_sites = len(site_rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    console.print(f"[cyan]Processing {total_sites} site(s). Writing to {output_path}[/cyan]")

    success_count = 0
    with output_path.open("w", encoding="utf-8") as output_file:
        for idx, row in enumerate(site_rows, start=1):
            site_id = int(row.site_id)
            site_name = row.name
            country = row.country

            console.rule(f"[bold]Site {idx}/{total_sites}: {site_name} ({country})[/bold]")
            try:
                site_details = format_site_details(site_name, country, engine)
                retrieval_agent = CandidateRetrievalAgent()
                retrieval_agent.set_task(site_details)

                console.print(f"[italic]Running agent for site_id={site_id}...[/italic]")
                start_time = datetime.utcnow()
                result = await retrieval_agent.run()
                duration = (datetime.utcnow() - start_time).total_seconds()

                record = {
                    "site_id": site_id,
                    "site_name": site_name,
                    "country": country,
                    "extracted_at": datetime.utcnow().isoformat(),
                    "duration_seconds": duration,
                    "result": result,
                    "agent": "BUAgent",
                }

                output_file.write(json.dumps(record, ensure_ascii=False) + "\n")
                output_file.flush()

                if result.get("is_successful"):
                    success_count += 1
                    structured_output = result.get("structured_output") or {}
                    candidates = len(structured_output.get("candidate_websites", []))
                    usage_stats = result.get("usage_stats") or {}
                    console.print(
                        f"[green]✓ Success. {candidates} candidate(s). "
                        f"Cost ${usage_stats.get('total_cost', 0):.4f}[/green]"
                    )
                else:
                    console.print("[yellow]Agent finished but marked as unsuccessful.[/yellow]")

            except Exception as exc:  # pragma: no cover - interactive command
                console.print(f"[red]Error processing {site_name} ({site_id}): {exc}[/red]")
                error_record = {
                    "site_id": site_id,
                    "site_name": site_name,
                    "country": country,
                    "extracted_at": datetime.utcnow().isoformat(),
                    "error": str(exc),
                    "result": None,
                    "agent": "BUAgent",
                }
                output_file.write(json.dumps(error_record, ensure_ascii=False) + "\n")
                output_file.flush()

    console.print(
        f"[bold green]Completed candidate retrieval. "
        f"{success_count}/{total_sites} successful run(s).[/bold green]"
    )


@app.command("candidate-validate")
def candidate_validate(
    candidate_ids: Optional[List[int]] = typer.Option(
        None,
        "--candidate-id",
        "-c",
        help="Specific candidate IDs to validate (repeat option for multiple).",
    ),
    site_ids: Optional[List[int]] = typer.Option(
        None,
        "--site-id",
        "-s",
        help="Filter candidates by site IDs.",
    ),
    host: Optional[str] = typer.Option(
        None,
        "--host",
        help="Filter by exact domain host.",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Limit number of candidates to validate.",
    ),
    only_unvalidated: bool = typer.Option(
        False,
        "--only-unvalidated",
        help="Include only candidates that have never been validated.",
    ),
    retry_failed: bool = typer.Option(
        False,
        "--retry-failed",
        help="Include only candidates whose latest validation was not successful.",
    ),
    headless: bool = typer.Option(True, help="Run browser headless."),
    timeout_ms: int = typer.Option(15000, help="Navigation timeout in milliseconds."),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional JSONL file to write validation results.",
    ),
    validated_by: str = typer.Option(
        "BUValidator",
        "--validated-by",
        help="Label stored with validation records.",
    ),
):
    """Validate candidate URLs via a real browser and store the results."""
    engine = get_engine()
    filters = {
        "candidate_ids": candidate_ids,
        "site_ids": site_ids,
        "host": host,
        "limit": limit,
        "only_unvalidated": only_unvalidated,
        "retry_failed": retry_failed,
    }
    candidates = fetch_candidates_for_validation(
        engine,
        candidate_ids=candidate_ids,
        site_ids=site_ids,
        host=host,
        limit=limit,
        only_unvalidated=only_unvalidated,
    )

    if retry_failed:
        candidates = [
            c
            for c in candidates
            if c.get("latest_status") and c.get("latest_status") != ValidationStatus.OK.value
        ]

    if not candidates:
        console.print("[yellow]No candidates match the provided filters.[/yellow]")
        raise typer.Exit()

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output_handle = output.open("w", encoding="utf-8")
    else:
        output_handle = None

    run_id = create_validation_run(
        engine,
        triggered_by="cli",
        validator="browser",
        filters=filters,
    )

    success = 0
    failure = 0
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Validating candidates...", total=len(candidates))
            validation_results = asyncio.run(
                _validate_candidates_async(
                    candidates,
                    headless=headless,
                    timeout_ms=timeout_ms,
                    progress=progress,
                    task_id=task,
                )
            )

        for candidate, result in validation_results:
            record_candidate_validation(
                engine,
                candidate_id=int(candidate["candidate_id"]),
                result=result,
                validation_run_id=run_id,
                validator="browser",
                validated_by=validated_by,
            )

            if output_handle:
                output_handle.write(
                    json.dumps(
                        {
                            **candidate,
                            "validation": asdict(result),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

            if result.status in (ValidationStatus.OK, ValidationStatus.REDIRECTED):
                success += 1
            else:
                failure += 1

    finally:
        if output_handle:
            output_handle.close()
        finalize_validation_run(
            engine,
            run_id,
            candidate_total=len(candidates),
            success_count=success,
            failure_count=failure,
        )

    console.print(
        f"[green]Validation run complete.[/green] "
        f"{success} succeeded / {failure} failed (run_id={run_id})."
    )


@app.command("candidate-validate-manual")
def candidate_validate_manual(
    candidate_id: int = typer.Option(
        ...,
        "--candidate-id",
        "-c",
        prompt=True,
        help="Candidate ID to annotate.",
    ),
    validated_by: str = typer.Option(
        "Human",
        "--validated-by",
        help="Label for the operator performing the validation.",
    ),
):
    """Record a manual validation decision for a candidate."""
    engine = get_engine()
    candidate = get_candidate_by_id(engine, candidate_id)
    if not candidate:
        console.print(f"[red]Candidate {candidate_id} not found.[/red]")
        raise typer.Exit(1)

    console.print("[bold cyan]Candidate details[/bold cyan]")
    console.print(
        f"Site ID: {candidate['site_id']} | Run ID: {candidate['run_id']} | "
        f"Name: {candidate.get('name') or '<unnamed>'}"
    )
    console.print(f"URL: {candidate['url']}")
    if candidate.get("latest_status"):
        console.print(
            f"Latest status: {candidate['latest_status']} "
            f"(at {candidate.get('latest_validated_at')})"
        )

    status_value = typer.prompt(
        "Validation status [ok/dead/redirected/blocked/timeout/error]",
        default="ok",
    ).strip().lower()
    try:
        status = ValidationStatus(status_value)
    except ValueError:
        console.print("[red]Invalid status provided.[/red]")
        raise typer.Exit(1)

    http_status = _prompt_optional_int("HTTP status code")
    latency_ms = _prompt_optional_int("Latency in ms")
    final_url_input = typer.prompt("Final URL (leave blank to keep original)", default="").strip()
    error_notes = typer.prompt("Error/notes (optional)", default="").strip() or None

    result = ValidationResult(
        status=status,
        http_status=http_status,
        final_url=final_url_input or candidate["url"],
        latency_ms=latency_ms,
        error=error_notes,
    )

    record_candidate_validation(
        engine,
        candidate_id=candidate_id,
        result=result,
        validation_run_id=None,
        validator="manual",
        validated_by=validated_by,
    )

    console.print(
        "[green]Manual validation recorded[/green] "
        f"(candidate_id={candidate_id}, status={result.status.value})."
    )


async def _validate_candidates_async(
    candidates: List[Dict[str, Any]],
    *,
    headless: bool,
    timeout_ms: int,
    progress: Progress | None = None,
    task_id: int | None = None,
):
    """Run browser validations sequentially while reusing a single browser."""
    validator = BrowserValidator(headless=headless, timeout_ms=timeout_ms)
    results: List[tuple[Dict[str, Any], Any]] = []
    try:
        for idx, candidate in enumerate(candidates, start=1):
            result = await validator.validate_url(candidate["url"])
            results.append((candidate, result))
            if progress and task_id is not None:
                label = candidate.get("name") or candidate.get("url")
                progress.update(
                    task_id,
                    advance=1,
                    description=f"Validating {label} ({idx}/{len(candidates)})",
                )
    finally:
        await validator.close()
    return results


@app.command("candidate-run")
def candidate_run(
    output: Path = typer.Option(
        Path("outputs/candidate_retrieval_results.jsonl"),
        "--output",
        "-o",
        help="Path to write JSONL results.",
    ),
    site_ids: Optional[List[int]] = typer.Option(
        None,
        "--site-id",
        "-s",
        help="Filter to specific site IDs (repeat option for multiple).",
    ),
    limit: Optional[int] = typer.Option(
        None,
        "--limit",
        "-l",
        help="Limit the number of sites to process after applying filters.",
    ),
):
    """Run the CandidateRetrievalAgent via the CLI."""
    engine = get_engine()
    sites_df = get_sites(engine)

    if site_ids:
        site_set = set(site_ids)
        sites_df = sites_df[sites_df["site_id"].isin(site_set)]

    if limit is not None:
        sites_df = sites_df.head(limit)

    if sites_df.empty:
        console.print("[yellow]No sites match the given filters.[/yellow]")
        raise typer.Exit(1)

    asyncio.run(
        _run_candidate_retrieval_for_sites(
            output_path=output,
            site_rows=list(sites_df.itertuples(index=False)),
            engine=engine,
        )
    )


if __name__ == "__main__":
    app()

