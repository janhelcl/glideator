"""CLI for ground crew data management."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import typer
from dotenv import load_dotenv
from sqlalchemy import create_engine
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .io import load_extraction_run

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


def get_engine():
    """Get database engine from environment variables."""
    load_dotenv()
    
    connection_string = "postgresql://{user}:{password}@{host}:{port}/{db}".format(
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT'),
        db=os.getenv('DB_NAME')
    )
    return create_engine(connection_string)


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


if __name__ == "__main__":
    app()

