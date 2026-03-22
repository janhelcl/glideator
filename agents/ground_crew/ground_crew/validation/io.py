"""Database helpers for candidate validation."""

from __future__ import annotations

import json
from typing import Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .models import ValidationResult


def create_validation_run(
    engine: Engine,
    *,
    triggered_by: str = "cli",
    validator: str = "browser",
    filters: Optional[Dict[str, object]] = None,
    notes: Optional[str] = None,
) -> int:
    """Insert a validation run record and return its id."""
    payload = {
        "triggered_by": triggered_by,
        "validator": validator,
        "filters": json.dumps(filters or {}),
        "notes": notes,
    }
    with engine.begin() as conn:
        run_id = conn.execute(
            text(
                """
                INSERT INTO glideator_ground_crew.candidate_validation_runs
                    (triggered_by, validator, filters, notes)
                VALUES (:triggered_by, :validator, (:filters)::jsonb, :notes)
                RETURNING validation_run_id
                """
            ),
            payload,
        ).scalar_one()
    return int(run_id)


def finalize_validation_run(
    engine: Engine,
    run_id: int,
    *,
    candidate_total: int,
    success_count: int,
    failure_count: int,
):
    """Mark a validation run as finished with summary stats."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE glideator_ground_crew.candidate_validation_runs
                SET finished_at = NOW(),
                    candidate_total = :candidate_total,
                    success_count = :success_count,
                    failure_count = :failure_count
                WHERE validation_run_id = :run_id
                """
            ),
            {
                "candidate_total": candidate_total,
                "success_count": success_count,
                "failure_count": failure_count,
                "run_id": run_id,
            },
        )


def record_candidate_validation(
    engine: Engine,
    *,
    candidate_id: int,
    result: ValidationResult,
    validation_run_id: Optional[int],
    validator: str = "browser",
    validated_by: Optional[str] = None,
) -> int:
    """Persist a single candidate validation result."""
    with engine.begin() as conn:
        validation_id = conn.execute(
            text(
                """
                INSERT INTO glideator_ground_crew.candidate_validations (
                    candidate_id,
                    validation_run_id,
                    status,
                    http_status,
                    final_url,
                    latency_ms,
                    error,
                    validator,
                    validated_by
                )
                VALUES (
                    :candidate_id,
                    :validation_run_id,
                    :status,
                    :http_status,
                    :final_url,
                    :latency_ms,
                    :error,
                    :validator,
                    :validated_by
                )
                RETURNING validation_id
                """
            ),
            {
                "candidate_id": candidate_id,
                "validation_run_id": validation_run_id,
                "status": result.status.value,
                "http_status": result.http_status,
                "final_url": result.final_url,
                "latency_ms": result.latency_ms,
                "error": result.error,
                "validator": validator,
                "validated_by": validated_by,
            },
        ).scalar_one()
    return int(validation_id)


def fetch_candidates_for_validation(
    engine: Engine,
    *,
    candidate_ids: Optional[List[int]] = None,
    site_ids: Optional[List[int]] = None,
    host: Optional[str] = None,
    limit: Optional[int] = None,
    only_unvalidated: bool = False,
) -> List[Dict[str, object]]:
    """Retrieve candidate rows with latest validation status metadata."""
    conditions = ["TRUE"]
    params: Dict[str, object] = {}

    if candidate_ids:
        conditions.append("c.candidate_id = ANY(:candidate_ids)")
        params["candidate_ids"] = candidate_ids
    if site_ids:
        conditions.append("r.site_id = ANY(:site_ids)")
        params["site_ids"] = site_ids
    if host:
        conditions.append("LOWER(c.host) = LOWER(:host)")
        params["host"] = host
    if only_unvalidated:
        conditions.append("latest.status IS NULL")

    query = f"""
        SELECT
            c.candidate_id,
            c.run_id,
            r.site_id,
            c.name,
            c.url,
            c.host,
            latest.status AS latest_status
        FROM glideator_ground_crew.extraction_candidates c
        JOIN glideator_ground_crew.extraction_runs r
            ON c.run_id = r.run_id
        LEFT JOIN LATERAL (
            SELECT status
            FROM glideator_ground_crew.candidate_validations v
            WHERE v.candidate_id = c.candidate_id
            ORDER BY v.validated_at DESC
            LIMIT 1
        ) latest ON TRUE
        WHERE {" AND ".join(conditions)}
        ORDER BY c.candidate_id
    """
    if limit is not None:
        query += " LIMIT :limit"
        params["limit"] = limit

    with engine.connect() as conn:
        rows = conn.execute(text(query), params).mappings().all()
    return [dict(row) for row in rows]


def get_candidate_by_id(engine: Engine, candidate_id: int) -> Optional[Dict[str, object]]:
    """Fetch a single candidate with basic metadata."""
    query = """
        SELECT
            c.candidate_id,
            c.run_id,
            r.site_id,
            r.agent,
            r.extracted_at,
            c.name,
            c.url,
            c.host,
            latest.status AS latest_status,
            latest.validated_at AS latest_validated_at
        FROM glideator_ground_crew.extraction_candidates c
        JOIN glideator_ground_crew.extraction_runs r
            ON c.run_id = r.run_id
        LEFT JOIN LATERAL (
            SELECT status, validated_at
            FROM glideator_ground_crew.candidate_validations v
            WHERE v.candidate_id = c.candidate_id
            ORDER BY v.validated_at DESC
            LIMIT 1
        ) latest ON TRUE
        WHERE c.candidate_id = :candidate_id
    """
    with engine.connect() as conn:
        row = conn.execute(text(query), {"candidate_id": candidate_id}).mappings().first()
    return dict(row) if row else None


