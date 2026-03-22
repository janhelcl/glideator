"""Resolve per-site resources from the latest extraction run (validated links + feature URLs).

Keep SQL aligned with backend/app/crud.py get_site_resources.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.engine import Engine


def _dedupe_urls_preserve_order(rows: Sequence[Dict[str, Any]], url_key: str) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for row in rows:
        u = (row.get(url_key) or "").strip()
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def fetch_site_resources(engine: Engine, site_id: int) -> Dict[str, Any]:
    """Return canonical resources for one site.

    Uses the **latest extraction run that has at least one validated** (ok/redirected)
    candidate. If a newer run exists but only has failed/unvalidated candidates (e.g. a
    manual test run), we still prefer the most recent *useful* BU/agent run so resources
    are not wiped. If no run has validated candidates, falls back to the latest run (empty
    local_resources).
    """
    with engine.connect() as conn:
        run_row = conn.execute(
            text(
                """
                SELECT r.run_id, r.extracted_at
                FROM glideator_ground_crew.extraction_runs r
                WHERE r.site_id = :site_id
                  AND EXISTS (
                    SELECT 1
                    FROM glideator_ground_crew.extraction_candidates c
                    LEFT JOIN LATERAL (
                        SELECT status
                        FROM glideator_ground_crew.candidate_validations v
                        WHERE v.candidate_id = c.candidate_id
                        ORDER BY v.validated_at DESC
                        LIMIT 1
                    ) latest ON TRUE
                    WHERE c.run_id = r.run_id
                      AND latest.status IN ('ok', 'redirected')
                  )
                ORDER BY r.extracted_at DESC NULLS LAST
                LIMIT 1
                """
            ),
            {"site_id": site_id},
        ).mappings().first()

        if not run_row:
            run_row = conn.execute(
                text(
                    """
                    SELECT run_id, extracted_at
                    FROM glideator_ground_crew.extraction_runs
                    WHERE site_id = :site_id
                    ORDER BY extracted_at DESC NULLS LAST
                    LIMIT 1
                    """
                ),
                {"site_id": site_id},
            ).mappings().first()

        if not run_row:
            return {
                "site_id": site_id,
                "source_run_id": None,
                "run_extracted_at": None,
                "local_resources": [],
                "webcam_url": None,
                "webcam_urls": [],
                "meteostation_url": None,
                "meteostation_urls": [],
            }

        run_id = int(run_row["run_id"])
        extracted_at = run_row["extracted_at"]
        if isinstance(extracted_at, datetime):
            run_extracted_at = extracted_at.isoformat()
        else:
            run_extracted_at = str(extracted_at) if extracted_at is not None else None

        candidates = conn.execute(
            text(
                """
                SELECT
                    c.candidate_id,
                    c.name,
                    c.url,
                    c.host,
                    c.takeoff_landing_areas,
                    c.rules,
                    c.fees,
                    c.access,
                    c.meteostation,
                    c.webcams
                FROM glideator_ground_crew.extraction_candidates c
                LEFT JOIN LATERAL (
                    SELECT status
                    FROM glideator_ground_crew.candidate_validations v
                    WHERE v.candidate_id = c.candidate_id
                    ORDER BY v.validated_at DESC
                    LIMIT 1
                ) latest ON TRUE
                WHERE c.run_id = :run_id
                  AND latest.status IN ('ok', 'redirected')
                ORDER BY c.candidate_id
                """
            ),
            {"run_id": run_id},
        ).mappings().all()

        local_resources = [dict(r) for r in candidates]
        candidate_ids = [int(r["candidate_id"]) for r in local_resources]

        webcam_urls: List[str] = []
        meteostation_urls: List[str] = []
        if candidate_ids:
            webcam_rows = conn.execute(
                text(
                    """
                    SELECT webcam_url, extracted_at
                    FROM glideator_ground_crew.webcam_extractions
                    WHERE candidate_id = ANY(:cids)
                      AND found = true
                      AND NULLIF(TRIM(webcam_url), '') IS NOT NULL
                    ORDER BY extracted_at DESC NULLS LAST
                    """
                ),
                {"cids": candidate_ids},
            ).mappings().all()
            webcam_urls = _dedupe_urls_preserve_order([dict(r) for r in webcam_rows], "webcam_url")

            meteo_rows = conn.execute(
                text(
                    """
                    SELECT meteostation_url, extracted_at
                    FROM glideator_ground_crew.meteostation_extractions
                    WHERE candidate_id = ANY(:cids)
                      AND found = true
                      AND NULLIF(TRIM(meteostation_url), '') IS NOT NULL
                    ORDER BY extracted_at DESC NULLS LAST
                    """
                ),
                {"cids": candidate_ids},
            ).mappings().all()
            meteostation_urls = _dedupe_urls_preserve_order(
                [dict(r) for r in meteo_rows], "meteostation_url"
            )

        return {
            "site_id": site_id,
            "source_run_id": run_id,
            "run_extracted_at": run_extracted_at,
            "local_resources": local_resources,
            "webcam_url": webcam_urls[0] if webcam_urls else None,
            "webcam_urls": webcam_urls,
            "meteostation_url": meteostation_urls[0] if meteostation_urls else None,
            "meteostation_urls": meteostation_urls,
        }


def fetch_all_site_ids_with_runs(engine: Engine) -> List[int]:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT DISTINCT site_id
                FROM glideator_ground_crew.extraction_runs
                ORDER BY site_id
                """
            )
        ).fetchall()
    return [int(r[0]) for r in rows]


def fetch_all_site_resources(engine: Engine) -> List[Dict[str, Any]]:
    """Export payload: one record per site that has at least one extraction run."""
    return [fetch_site_resources(engine, sid) for sid in fetch_all_site_ids_with_runs(engine)]
