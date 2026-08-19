from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from . import admin

router = APIRouter(prefix="/admin", tags=["Admin"])


class AnalyticsFunnel(admin.AnalyticsFunnel):
    planner_sessions: int = 0


class AdminAnalyticsResponse(admin.AdminAnalyticsResponse):
    map_to_site_sessions: int = 0
    map_site_open_events: int = 0
    sites_opened_per_map_session: float = 0
    trip_planner: AnalyticsFunnel


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 2)


@router.get("/analytics", response_model=AdminAnalyticsResponse)
async def get_analytics(
    days: int = Query(default=30, ge=1, le=365),
    _: models.User = Depends(admin.require_admin),
    db: AsyncSession = Depends(admin.get_db),
):
    # Reuse the legacy endpoint for the broad analytics payload and replace only
    # the engagement metrics whose denominators need session sequencing.
    base = await admin.get_analytics(days=days, _=_, db=db)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    engagement_row = (
        await db.execute(
            text(
                """
                WITH scoped AS (
                    SELECT event_id, session_id, event_name, path, created_at
                    FROM product_events
                    WHERE created_at >= :cutoff
                ),
                map_entries AS (
                    SELECT session_id, MIN(created_at) AS first_map_at
                    FROM scoped
                    WHERE event_name = 'page_view' AND path = '/'
                    GROUP BY session_id
                ),
                map_activity AS (
                    SELECT
                        m.session_id,
                        COUNT(e.event_id) FILTER (
                            WHERE e.event_name = 'site_detail_viewed'
                              AND e.created_at >= m.first_map_at
                        ) AS site_open_events
                    FROM map_entries m
                    LEFT JOIN scoped e ON e.session_id = m.session_id
                    GROUP BY m.session_id
                ),
                planner_entries AS (
                    SELECT session_id, MIN(created_at) AS first_planner_at
                    FROM scoped
                    WHERE event_name = 'page_view' AND path = '/trip-planner'
                    GROUP BY session_id
                ),
                planner_activity AS (
                    SELECT
                        p.session_id,
                        COUNT(e.event_id) FILTER (
                            WHERE e.event_name = 'trip_plan_submitted'
                              AND e.created_at >= p.first_planner_at
                        ) AS submits,
                        COUNT(e.event_id) FILTER (
                            WHERE e.event_name = 'trip_plan_results_viewed'
                              AND e.created_at >= p.first_planner_at
                        ) AS results,
                        COUNT(e.event_id) FILTER (
                            WHERE e.event_name = 'trip_plan_site_opened'
                              AND e.created_at >= p.first_planner_at
                        ) AS site_opens
                    FROM planner_entries p
                    LEFT JOIN scoped e ON e.session_id = p.session_id
                    GROUP BY p.session_id
                )
                SELECT
                    (SELECT COUNT(*) FROM map_entries) AS map_sessions,
                    (
                        SELECT COUNT(*)
                        FROM map_activity
                        WHERE site_open_events > 0
                    ) AS map_to_site_sessions,
                    (
                        SELECT COALESCE(SUM(site_open_events), 0)
                        FROM map_activity
                    ) AS map_site_open_events,
                    (SELECT COUNT(*) FROM planner_entries) AS planner_sessions,
                    (
                        SELECT COUNT(*)
                        FROM planner_activity
                        WHERE submits > 0
                    ) AS submitted_sessions,
                    (
                        SELECT COUNT(*)
                        FROM planner_activity
                        WHERE results > 0
                    ) AS results_sessions,
                    (
                        SELECT COUNT(*)
                        FROM planner_activity
                        WHERE results > 0 AND site_opens > 0
                    ) AS opened_site_sessions
                """
            ),
            {"cutoff": cutoff},
        )
    ).mappings().one()

    map_sessions = int(engagement_row["map_sessions"] or 0)
    map_to_site_sessions = int(engagement_row["map_to_site_sessions"] or 0)
    map_site_open_events = int(engagement_row["map_site_open_events"] or 0)
    planner_sessions = int(engagement_row["planner_sessions"] or 0)
    submitted_sessions = int(engagement_row["submitted_sessions"] or 0)
    results_sessions = int(engagement_row["results_sessions"] or 0)
    opened_site_sessions = int(engagement_row["opened_site_sessions"] or 0)

    payload = base.model_dump()
    payload.update(
        map_sessions=map_sessions,
        map_to_site_sessions=map_to_site_sessions,
        map_site_open_events=map_site_open_events,
        sites_opened_per_map_session=_ratio(map_site_open_events, map_sessions),
        map_to_site_rate=admin._rate(map_to_site_sessions, map_sessions),
        trip_planner={
            **base.trip_planner.model_dump(),
            "planner_sessions": planner_sessions,
            "submitted_sessions": submitted_sessions,
            "results_sessions": results_sessions,
            "opened_site_sessions": opened_site_sessions,
            "results_rate": admin._rate(results_sessions, planner_sessions),
            "site_open_rate": admin._rate(opened_site_sessions, results_sessions),
        },
    )
    return AdminAnalyticsResponse(**payload)
