from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from .admin import (
    AnalyticsDailyPoint,
    AnalyticsEventCount,
    AnalyticsFeedbackSurface,
    AnalyticsPathCount,
    AnalyticsSiteInteraction,
    get_db,
    require_admin,
    _rate,
)
from .analytics import ProductEvent

router = APIRouter(prefix="/admin", tags=["Admin"])


class AnalyticsFunnel(BaseModel):
    planner_sessions: int = 0
    submitted_sessions: int = 0
    results_sessions: int = 0
    opened_site_sessions: int = 0
    results_rate: float = 0
    site_open_rate: float = 0


class AdminAnalyticsResponse(BaseModel):
    window_days: int
    total_events: int
    unique_visitors: int
    unique_sessions: int
    map_sessions: int
    site_detail_sessions: int
    map_to_site_sessions: int
    map_site_open_events: int
    sites_opened_per_map_session: float
    map_to_site_rate: float
    daily: List[AnalyticsDailyPoint]
    event_counts: List[AnalyticsEventCount]
    top_paths: List[AnalyticsPathCount]
    trip_planner: AnalyticsFunnel
    recommendation_feedback: List[AnalyticsFeedbackSurface]
    top_sites: List[AnalyticsSiteInteraction]


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 2)


@router.get("/analytics", response_model=AdminAnalyticsResponse)
async def get_analytics(
    days: int = Query(default=30, ge=1, le=365),
    _: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    summary = (
        await db.execute(
            select(
                func.count(ProductEvent.event_id),
                func.count(func.distinct(ProductEvent.anonymous_id)),
                func.count(func.distinct(ProductEvent.session_id)),
            ).where(ProductEvent.created_at >= cutoff)
        )
    ).one()

    daily_result = await db.execute(
        text(
            """
            SELECT
                date_trunc('day', created_at)::date AS day,
                COUNT(DISTINCT anonymous_id) AS visitors,
                COUNT(DISTINCT session_id) AS sessions,
                COUNT(*) AS events
            FROM product_events
            WHERE created_at >= :cutoff
            GROUP BY 1
            ORDER BY 1
            """
        ),
        {"cutoff": cutoff},
    )
    daily = [
        AnalyticsDailyPoint(
            day=row["day"].isoformat(),
            visitors=int(row["visitors"] or 0),
            sessions=int(row["sessions"] or 0),
            events=int(row["events"] or 0),
        )
        for row in daily_result.mappings().all()
    ]

    event_result = await db.execute(
        text(
            """
            SELECT
                event_name,
                COUNT(*) AS events,
                COUNT(DISTINCT anonymous_id) AS visitors
            FROM product_events
            WHERE created_at >= :cutoff
            GROUP BY event_name
            ORDER BY events DESC, event_name
            """
        ),
        {"cutoff": cutoff},
    )
    event_counts = [AnalyticsEventCount(**dict(row)) for row in event_result.mappings().all()]

    path_result = await db.execute(
        text(
            """
            SELECT
                COALESCE(NULLIF(path, ''), '(unknown)') AS path,
                COUNT(*) AS events,
                COUNT(DISTINCT anonymous_id) AS visitors
            FROM product_events
            WHERE created_at >= :cutoff
            GROUP BY 1
            ORDER BY events DESC, path
            LIMIT 20
            """
        ),
        {"cutoff": cutoff},
    )
    top_paths = [AnalyticsPathCount(**dict(row)) for row in path_result.mappings().all()]

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
                        SELECT COUNT(DISTINCT session_id)
                        FROM scoped
                        WHERE event_name = 'site_detail_viewed'
                    ) AS site_detail_sessions,
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
    site_detail_sessions = int(engagement_row["site_detail_sessions"] or 0)
    map_to_site_sessions = int(engagement_row["map_to_site_sessions"] or 0)
    map_site_open_events = int(engagement_row["map_site_open_events"] or 0)
    planner_sessions = int(engagement_row["planner_sessions"] or 0)
    submitted_sessions = int(engagement_row["submitted_sessions"] or 0)
    results_sessions = int(engagement_row["results_sessions"] or 0)
    opened_site_sessions = int(engagement_row["opened_site_sessions"] or 0)

    feedback_result = await db.execute(
        text(
            """
            SELECT
                COALESCE(NULLIF(properties ->> 'surface', ''), '(unknown)') AS surface,
                COUNT(*) FILTER (WHERE properties ->> 'rating' = 'helpful') AS helpful,
                COUNT(*) FILTER (WHERE properties ->> 'rating' = 'not_helpful') AS not_helpful,
                COUNT(*) AS total
            FROM product_events
            WHERE created_at >= :cutoff
              AND event_name = 'recommendation_feedback_submitted'
            GROUP BY 1
            ORDER BY total DESC, surface
            """
        ),
        {"cutoff": cutoff},
    )
    recommendation_feedback = []
    for row in feedback_result.mappings().all():
        helpful = int(row["helpful"] or 0)
        total = int(row["total"] or 0)
        recommendation_feedback.append(
            AnalyticsFeedbackSurface(
                surface=row["surface"],
                helpful=helpful,
                not_helpful=int(row["not_helpful"] or 0),
                total=total,
                helpful_rate=_rate(helpful, total) if total else None,
            )
        )

    top_sites_result = await db.execute(
        text(
            """
            SELECT
                NULLIF(e.properties ->> 'site_id', '')::integer AS site_id,
                MAX(s.name) AS site_name,
                COUNT(*) AS interactions,
                COUNT(DISTINCT e.anonymous_id) AS visitors
            FROM product_events e
            LEFT JOIN sites s
              ON s.site_id = NULLIF(e.properties ->> 'site_id', '')::integer
            WHERE e.created_at >= :cutoff
              AND e.event_name IN ('site_detail_viewed', 'trip_plan_site_opened')
              AND NULLIF(e.properties ->> 'site_id', '') IS NOT NULL
            GROUP BY 1
            ORDER BY interactions DESC, site_id
            LIMIT 15
            """
        ),
        {"cutoff": cutoff},
    )
    top_sites = [
        AnalyticsSiteInteraction(**dict(row)) for row in top_sites_result.mappings().all()
    ]

    return AdminAnalyticsResponse(
        window_days=days,
        total_events=int(summary[0] or 0),
        unique_visitors=int(summary[1] or 0),
        unique_sessions=int(summary[2] or 0),
        map_sessions=map_sessions,
        site_detail_sessions=site_detail_sessions,
        map_to_site_sessions=map_to_site_sessions,
        map_site_open_events=map_site_open_events,
        sites_opened_per_map_session=_ratio(map_site_open_events, map_sessions),
        map_to_site_rate=_rate(map_to_site_sessions, map_sessions),
        daily=daily,
        event_counts=event_counts,
        top_paths=top_paths,
        trip_planner=AnalyticsFunnel(
            planner_sessions=planner_sessions,
            submitted_sessions=submitted_sessions,
            results_sessions=results_sessions,
            opened_site_sessions=opened_site_sessions,
            results_rate=_rate(results_sessions, planner_sessions),
            site_open_rate=_rate(opened_site_sessions, results_sessions),
        ),
        recommendation_feedback=recommendation_feedback,
        top_sites=top_sites,
    )
