"""CLI for ground crew data management."""

import json
import os
from pathlib import Path

import typer
from dotenv import load_dotenv
from sqlalchemy import create_engine
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .io import load_extraction_run

app = typer.Typer(help="Ground Crew - Manage extraction run data")
console = Console()


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


if __name__ == "__main__":
    app()

