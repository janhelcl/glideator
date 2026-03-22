"""I/O operations for loading extraction run data to the database."""

from typing import Any, Dict
from urllib.parse import urlsplit
from sqlalchemy import text
from sqlalchemy.engine import Engine


def extract_domain(url: str) -> str:
    """Extract domain/host from URL.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Lowercase hostname/domain
    """
    parsed = urlsplit(url.strip())
    host = (parsed.hostname or "").lower()
    return host


def load_extraction_run(
    data: Dict[str, Any],
    engine: Engine
) -> int:
    """Load an extraction run and its candidates to the database.
    
    Takes a JSON object from candidate_retrieval_results.jsonl and loads it
    to both extraction_runs and extraction_candidates tables.
    
    Args:
        data: Dictionary containing extraction run data with keys:
            - site_id: int
            - extracted_at: ISO timestamp string
            - duration_seconds: float
            - agent: agent name (BUAgent/Human)
            - result: dict with usage_stats (containing by_model) and structured_output
        engine: SQLAlchemy engine for database connection
        
    Returns:
        run_id: The ID of the inserted extraction run
        
    Example:
        >>> import json
        >>> from sqlalchemy import create_engine
        >>> 
        >>> engine = create_engine("postgresql://user:pass@localhost/db")
        >>> with open("candidate_retrieval_results.jsonl") as f:
        >>>     for line in f:
        >>>         data = json.loads(line)
        >>>         run_id = load_extraction_run(data, engine)
        >>>         print(f"Loaded run {run_id}")
    """
    # Extract extraction_run data
    site_id = data["site_id"]
    extracted_at = data["extracted_at"]
    duration_seconds = data["duration_seconds"]
    
    # Get agent from data
    agent_name = data.get("agent", "BUAgent")
    
    # Extract usage statistics
    usage_stats = data["result"]["usage_stats"]
    
    # Extract model from by_model dictionary (first key is the model name)
    model_name = None
    if "by_model" in usage_stats and usage_stats["by_model"]:
        # Get the first (and typically only) model name from by_model dict
        model_name = list(usage_stats["by_model"].keys())[0]
    
    # Build extraction_run record
    run_data = {
        "site_id": site_id,
        "agent": agent_name,
        "model": model_name,
        "extracted_at": extracted_at,
        "duration_seconds": duration_seconds,
        "usage_total_prompt_tokens": usage_stats.get("total_prompt_tokens"),
        "usage_total_prompt_cost": usage_stats.get("total_prompt_cost"),
        "usage_total_prompt_cached_tokens": usage_stats.get("total_prompt_cached_tokens"),
        "usage_total_prompt_cached_cost": usage_stats.get("total_prompt_cached_cost"),
        "usage_total_completion_tokens": usage_stats.get("total_completion_tokens"),
        "usage_total_completion_cost": usage_stats.get("total_completion_cost"),
        "usage_total_tokens": usage_stats.get("total_tokens"),
        "usage_total_cost": usage_stats.get("total_cost"),
        "usage_entry_count": usage_stats.get("entry_count"),
        "candidate_count": len(data["result"]["structured_output"]["candidate_websites"]),
    }
    
    # Insert extraction_run and get run_id
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO glideator_ground_crew.extraction_runs (
                    site_id, agent, model, extracted_at, duration_seconds,
                    usage_total_prompt_tokens, usage_total_prompt_cost,
                    usage_total_prompt_cached_tokens, usage_total_prompt_cached_cost,
                    usage_total_completion_tokens, usage_total_completion_cost,
                    usage_total_tokens, usage_total_cost, usage_entry_count,
                    candidate_count
                )
                VALUES (
                    :site_id, :agent, :model, :extracted_at, :duration_seconds,
                    :usage_total_prompt_tokens, :usage_total_prompt_cost,
                    :usage_total_prompt_cached_tokens, :usage_total_prompt_cached_cost,
                    :usage_total_completion_tokens, :usage_total_completion_cost,
                    :usage_total_tokens, :usage_total_cost, :usage_entry_count,
                    :candidate_count
                )
                RETURNING run_id
            """),
            run_data
        )
        run_id = result.scalar_one()
        
        # Insert candidates
        candidates = data["result"]["structured_output"]["candidate_websites"]
        for candidate in candidates:
            candidate_data = {
                "run_id": run_id,
                "name": candidate.get("name"),
                "url": candidate.get("url"),
                "host": extract_domain(candidate.get("url", "")),
                "takeoff_landing_areas": candidate["evidence"].get("takeoff_landing_areas"),
                "rules": candidate["evidence"].get("rules"),
                "fees": candidate["evidence"].get("fees"),
                "access": candidate["evidence"].get("access"),
                "meteostation": candidate["evidence"].get("meteostation"),
                "webcams": candidate["evidence"].get("webcams"),
            }
            
            conn.execute(
                text("""
                    INSERT INTO glideator_ground_crew.extraction_candidates (
                        run_id, name, url, host,
                        takeoff_landing_areas, rules, fees, access,
                        meteostation, webcams
                    )
                    VALUES (
                        :run_id, :name, :url, :host,
                        :takeoff_landing_areas, :rules, :fees, :access,
                        :meteostation, :webcams
                    )
                """),
                candidate_data
            )
    
    return run_id

