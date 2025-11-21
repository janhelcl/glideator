"""CLI for ground crew data management."""

import asyncio
import json
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

