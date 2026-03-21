"""Database helpers for webcam and meteostation feature extractions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine


def record_webcam_extraction(
    engine: Engine,
    *,
    candidate_id: int,
    found: bool,
    webcam_url: Optional[str],
    agent: str = "BUAgent",
    model: Optional[str] = None,
    duration_seconds: Optional[float] = None,
    usage_total_tokens: Optional[int] = None,
    usage_total_cost: Optional[float] = None,
) -> int:
    with engine.begin() as conn:
        extraction_id = conn.execute(
            text("""
                INSERT INTO glideator_ground_crew.webcam_extractions (
                    candidate_id, found, webcam_url, agent, model,
                    duration_seconds, usage_total_tokens, usage_total_cost
                ) VALUES (
                    :candidate_id, :found, :webcam_url, :agent, :model,
                    :duration_seconds, :usage_total_tokens, :usage_total_cost
                )
                RETURNING extraction_id
            """),
            {
                "candidate_id": candidate_id,
                "found": found,
                "webcam_url": webcam_url,
                "agent": agent,
                "model": model,
                "duration_seconds": duration_seconds,
                "usage_total_tokens": usage_total_tokens,
                "usage_total_cost": usage_total_cost,
            },
        ).scalar_one()
    return int(extraction_id)


def record_meteostation_extraction(
    engine: Engine,
    *,
    candidate_id: int,
    found: bool,
    meteostation_url: Optional[str],
    agent: str = "BUAgent",
    model: Optional[str] = None,
    duration_seconds: Optional[float] = None,
    usage_total_tokens: Optional[int] = None,
    usage_total_cost: Optional[float] = None,
) -> int:
    with engine.begin() as conn:
        extraction_id = conn.execute(
            text("""
                INSERT INTO glideator_ground_crew.meteostation_extractions (
                    candidate_id, found, meteostation_url, agent, model,
                    duration_seconds, usage_total_tokens, usage_total_cost
                ) VALUES (
                    :candidate_id, :found, :meteostation_url, :agent, :model,
                    :duration_seconds, :usage_total_tokens, :usage_total_cost
                )
                RETURNING extraction_id
            """),
            {
                "candidate_id": candidate_id,
                "found": found,
                "meteostation_url": meteostation_url,
                "agent": agent,
                "model": model,
                "duration_seconds": duration_seconds,
                "usage_total_tokens": usage_total_tokens,
                "usage_total_cost": usage_total_cost,
            },
        ).scalar_one()
    return int(extraction_id)


def fetch_candidates_for_feature_extraction(
    engine: Engine,
    *,
    feature: str,
    candidate_ids: Optional[List[int]] = None,
    site_ids: Optional[List[int]] = None,
    limit: Optional[int] = None,
    only_unextracted: bool = False,
    only_validated_ok: bool = True,
) -> List[Dict[str, Any]]:
    """Retrieve candidates eligible for webcam or meteostation extraction.

    Args:
        feature: 'webcam' or 'meteostation' — controls which evidence flag
                 and which extraction table to check.
        only_validated_ok: When True (default), only include candidates whose
                          latest validation status is 'ok' or 'redirected'.
    """
    if feature not in ("webcam", "meteostation"):
        raise ValueError(f"feature must be 'webcam' or 'meteostation', got {feature!r}")

    evidence_col = "webcams" if feature == "webcam" else "meteostation"
    extraction_table = (
        "glideator_ground_crew.webcam_extractions"
        if feature == "webcam"
        else "glideator_ground_crew.meteostation_extractions"
    )

    conditions = [f"c.{evidence_col} = TRUE"]
    params: Dict[str, Any] = {}

    if candidate_ids:
        conditions.append("c.candidate_id = ANY(:candidate_ids)")
        params["candidate_ids"] = candidate_ids
    if site_ids:
        conditions.append("r.site_id = ANY(:site_ids)")
        params["site_ids"] = site_ids
    if only_validated_ok:
        conditions.append("latest_val.status IN ('ok', 'redirected')")
    if only_unextracted:
        conditions.append("prev_ext.extraction_id IS NULL")

    query = f"""
        SELECT
            c.candidate_id,
            c.run_id,
            r.site_id,
            c.name,
            c.url,
            c.host,
            latest_val.status AS validation_status
        FROM glideator_ground_crew.extraction_candidates c
        JOIN glideator_ground_crew.extraction_runs r
            ON c.run_id = r.run_id
        LEFT JOIN LATERAL (
            SELECT status
            FROM glideator_ground_crew.candidate_validations v
            WHERE v.candidate_id = c.candidate_id
            ORDER BY v.validated_at DESC
            LIMIT 1
        ) latest_val ON TRUE
        LEFT JOIN LATERAL (
            SELECT extraction_id
            FROM {extraction_table} e
            WHERE e.candidate_id = c.candidate_id
            LIMIT 1
        ) prev_ext ON TRUE
        WHERE {" AND ".join(conditions)}
        ORDER BY c.candidate_id
    """
    if limit is not None:
        query += " LIMIT :limit"
        params["limit"] = limit

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().all()
    return [dict(row) for row in rows]
