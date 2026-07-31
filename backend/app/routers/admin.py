import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, models
from ..celery_client import celery
from ..database import AsyncSessionLocal
from ..security import decode_token, effective_role, is_admin_identity
from .analytics import ProductEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def require_admin(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> models.User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    payload = decode_token(authorization.split(" ", 1)[1])
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = await db.get(models.User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    if not is_admin_identity(email=user.email, role=user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user


class AdminOverview(BaseModel):
    total_sites: int
    latest_gfs_forecast_at: Optional[datetime] = None
    latest_computed_at: Optional[datetime] = None
    covered_sites: int = 0
    coverage_percent: float = 0
    forecast_start_date: Optional[str] = None
    forecast_end_date: Optional[str] = None
    resource_sites: Optional[int] = None
    resource_coverage_percent: Optional[float] = None
    total_users: int = 0
    new_users_30d: int = 0
    feedback_count: int = 0
    visitors_30d: int = 0
    sessions_30d: int = 0


class ForecastRunSummary(BaseModel):
    gfs_forecast_at: datetime
    computed_at: datetime
    completed_at: datetime
    covered_sites: int
    expected_sites: int
    coverage_percent: float
    prediction_rows: int
    forecast_start_date: str
    forecast_end_date: str
    status: str


class AdminSite(BaseModel):
    site_id: int
    name: str
    latitude: float
    longitude: float
    altitude: int
    lat_gfs: float
    lon_gfs: float
    country: Optional[str] = None
    html: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    latest_gfs_forecast_at: Optional[datetime] = None


class AdminSiteUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    altitude: Optional[int] = Field(default=None, ge=-500, le=9000)
    lat_gfs: Optional[float] = Field(default=None, ge=-90, le=90)
    lon_gfs: Optional[float] = Field(default=None, ge=-180, le=360)
    country: Optional[str] = Field(default=None, max_length=120)
    html: Optional[str] = None
    tags: Optional[List[str]] = None


class AdminResourceLink(BaseModel):
    candidate_id: int
    name: Optional[str] = None
    url: str
    host: Optional[str] = None
    takeoff_landing_areas: Optional[bool] = None
    rules: Optional[bool] = None
    fees: Optional[bool] = None
    access: Optional[bool] = None
    meteostation: Optional[bool] = None
    webcams: Optional[bool] = None


class AdminResourceSite(BaseModel):
    site_id: int
    site_name: str
    source_run_id: Optional[int] = None
    run_extracted_at: Optional[datetime] = None
    resources: List[AdminResourceLink] = Field(default_factory=list)
    webcam_urls: List[str] = Field(default_factory=list)
    meteostation_urls: List[str] = Field(default_factory=list)


class AdminResourcePage(BaseModel):
    items: List[AdminResourceSite]
    total: int
    offset: int
    limit: int


class AdminUserRow(BaseModel):
    user_id: int
    email: str
    display_name: Optional[str] = None
    is_active: bool
    role: str
    created_at: datetime
    favorite_count: int = 0
    notification_count: int = 0
    active_push_subscriptions: int = 0


class AdminUsersResponse(BaseModel):
    total_users: int
    active_users: int
    new_users_7d: int
    new_users_30d: int
    users_with_favorites: int
    users_with_notifications: int
    users_with_push: int
    items: List[AdminUserRow]


class AdminFeedbackRow(BaseModel):
    id: int
    message: str
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    display_name: Optional[str] = None
    created_at: datetime


class AdminFeedbackResponse(BaseModel):
    total: int
    items: List[AdminFeedbackRow]


class AnalyticsDailyPoint(BaseModel):
    day: str
    visitors: int
    sessions: int
    events: int


class AnalyticsEventCount(BaseModel):
    event_name: str
    events: int
    visitors: int


class AnalyticsPathCount(BaseModel):
    path: str
    events: int
    visitors: int


class AnalyticsFunnel(BaseModel):
    submitted_sessions: int = 0
    results_sessions: int = 0
    opened_site_sessions: int = 0
    results_rate: float = 0
    site_open_rate: float = 0


class AnalyticsFeedbackSurface(BaseModel):
    surface: str
    helpful: int = 0
    not_helpful: int = 0
    total: int = 0
    helpful_rate: Optional[float] = None


class AnalyticsSiteInteraction(BaseModel):
    site_id: Optional[int] = None
    site_name: Optional[str] = None
    interactions: int
    visitors: int


class AdminAnalyticsResponse(BaseModel):
    window_days: int
    total_events: int
    unique_visitors: int
    unique_sessions: int
    map_sessions: int
    site_detail_sessions: int
    map_to_site_rate: float
    daily: List[AnalyticsDailyPoint]
    event_counts: List[AnalyticsEventCount]
    top_paths: List[AnalyticsPathCount]
    trip_planner: AnalyticsFunnel
    recommendation_feedback: List[AnalyticsFeedbackSurface]
    top_sites: List[AnalyticsSiteInteraction]


class AdminOperation(BaseModel):
    operation: str
    task_id: str
    status: str = "queued"


async def _resource_site_count(db: AsyncSession) -> Optional[int]:
    json_index = crud._site_resources_json_index()
    if json_index is not None:
        return sum(
            1
            for row in json_index.values()
            if row.get("local_resources") or row.get("webcam_urls") or row.get("meteostation_urls")
        )

    try:
        result = await db.execute(
            text(
                """
                SELECT COUNT(DISTINCT r.site_id)
                FROM glideator_ground_crew.extraction_runs r
                WHERE EXISTS (
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
                """
            )
        )
        return int(result.scalar_one() or 0)
    except SQLAlchemyError:
        await db.rollback()
        logger.info("Ground Crew resource tables are unavailable", exc_info=True)
        return None


def _coverage_percent(covered: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(100 * covered / total, 1)


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(100 * numerator / denominator, 1)


@router.get("/overview", response_model=AdminOverview)
async def get_overview(
    _: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total_sites = int((await db.execute(select(func.count(models.Site.site_id)))).scalar_one() or 0)
    latest_cycle = (await db.execute(select(func.max(models.Prediction.gfs_forecast_at)))).scalar_one_or_none()

    covered_sites = 0
    latest_computed_at = None
    forecast_start_date = None
    forecast_end_date = None
    if latest_cycle is not None:
        row = (
            await db.execute(
                select(
                    func.count(func.distinct(models.Prediction.site_id)),
                    func.max(models.Prediction.computed_at),
                    func.min(models.Prediction.date),
                    func.max(models.Prediction.date),
                ).where(models.Prediction.gfs_forecast_at == latest_cycle)
            )
        ).one()
        covered_sites = int(row[0] or 0)
        latest_computed_at = row[1]
        forecast_start_date = row[2].isoformat() if row[2] else None
        forecast_end_date = row[3].isoformat() if row[3] else None

    resource_sites = await _resource_site_count(db)
    cutoff_30d = datetime.now(timezone.utc) - timedelta(days=30)
    total_users = int((await db.execute(select(func.count(models.User.user_id)))).scalar_one() or 0)
    new_users_30d = int(
        (
            await db.execute(
                select(func.count(models.User.user_id)).where(models.User.created_at >= cutoff_30d)
            )
        ).scalar_one()
        or 0
    )
    feedback_count = int(
        (await db.execute(select(func.count(models.FeedbackSubmission.id)))).scalar_one() or 0
    )
    analytics_row = (
        await db.execute(
            select(
                func.count(ProductEvent.event_id),
                func.count(func.distinct(ProductEvent.anonymous_id)),
                func.count(func.distinct(ProductEvent.session_id)),
            ).where(ProductEvent.created_at >= cutoff_30d)
        )
    ).one()

    return AdminOverview(
        total_sites=total_sites,
        latest_gfs_forecast_at=latest_cycle,
        latest_computed_at=latest_computed_at,
        covered_sites=covered_sites,
        coverage_percent=_coverage_percent(covered_sites, total_sites),
        forecast_start_date=forecast_start_date,
        forecast_end_date=forecast_end_date,
        resource_sites=resource_sites,
        resource_coverage_percent=(
            _coverage_percent(resource_sites, total_sites) if resource_sites is not None else None
        ),
        total_users=total_users,
        new_users_30d=new_users_30d,
        feedback_count=feedback_count,
        visitors_30d=int(analytics_row[1] or 0),
        sessions_30d=int(analytics_row[2] or 0),
    )


@router.get("/users", response_model=AdminUsersResponse)
async def list_users(
    limit: int = Query(default=100, ge=1, le=500),
    _: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    cutoff_7d = now - timedelta(days=7)
    cutoff_30d = now - timedelta(days=30)

    summary_row = (
        await db.execute(
            select(
                func.count(models.User.user_id),
                func.count(models.User.user_id).filter(models.User.is_active.is_(True)),
                func.count(models.User.user_id).filter(models.User.created_at >= cutoff_7d),
                func.count(models.User.user_id).filter(models.User.created_at >= cutoff_30d),
            )
        )
    ).one()
    users_with_favorites = int(
        (
            await db.execute(select(func.count(func.distinct(models.UserFavorite.user_id))))
        ).scalar_one()
        or 0
    )
    users_with_notifications = int(
        (
            await db.execute(select(func.count(func.distinct(models.UserNotification.user_id))))
        ).scalar_one()
        or 0
    )
    users_with_push = int(
        (
            await db.execute(
                select(func.count(func.distinct(models.PushSubscription.user_id))).where(
                    models.PushSubscription.is_active.is_(True)
                )
            )
        ).scalar_one()
        or 0
    )

    favorite_counts = (
        select(
            models.UserFavorite.user_id.label("user_id"),
            func.count().label("favorite_count"),
        )
        .group_by(models.UserFavorite.user_id)
        .subquery()
    )
    notification_counts = (
        select(
            models.UserNotification.user_id.label("user_id"),
            func.count().label("notification_count"),
        )
        .group_by(models.UserNotification.user_id)
        .subquery()
    )
    push_counts = (
        select(
            models.PushSubscription.user_id.label("user_id"),
            func.count().label("push_count"),
        )
        .where(models.PushSubscription.is_active.is_(True))
        .group_by(models.PushSubscription.user_id)
        .subquery()
    )

    result = await db.execute(
        select(
            models.User,
            models.UserProfile.display_name,
            func.coalesce(favorite_counts.c.favorite_count, 0),
            func.coalesce(notification_counts.c.notification_count, 0),
            func.coalesce(push_counts.c.push_count, 0),
        )
        .outerjoin(models.UserProfile, models.UserProfile.user_id == models.User.user_id)
        .outerjoin(favorite_counts, favorite_counts.c.user_id == models.User.user_id)
        .outerjoin(notification_counts, notification_counts.c.user_id == models.User.user_id)
        .outerjoin(push_counts, push_counts.c.user_id == models.User.user_id)
        .order_by(models.User.created_at.desc())
        .limit(limit)
    )

    items = [
        AdminUserRow(
            user_id=user.user_id,
            email=user.email,
            display_name=display_name,
            is_active=user.is_active,
            role=effective_role(email=user.email, role=user.role),
            created_at=user.created_at,
            favorite_count=int(favorite_count or 0),
            notification_count=int(notification_count or 0),
            active_push_subscriptions=int(push_count or 0),
        )
        for user, display_name, favorite_count, notification_count, push_count in result.all()
    ]

    return AdminUsersResponse(
        total_users=int(summary_row[0] or 0),
        active_users=int(summary_row[1] or 0),
        new_users_7d=int(summary_row[2] or 0),
        new_users_30d=int(summary_row[3] or 0),
        users_with_favorites=users_with_favorites,
        users_with_notifications=users_with_notifications,
        users_with_push=users_with_push,
        items=items,
    )


@router.get("/feedback", response_model=AdminFeedbackResponse)
async def list_feedback(
    limit: int = Query(default=100, ge=1, le=500),
    _: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total = int(
        (await db.execute(select(func.count(models.FeedbackSubmission.id)))).scalar_one() or 0
    )
    result = await db.execute(
        select(
            models.FeedbackSubmission,
            models.User.email,
            models.UserProfile.display_name,
        )
        .outerjoin(models.User, models.User.user_id == models.FeedbackSubmission.user_id)
        .outerjoin(models.UserProfile, models.UserProfile.user_id == models.FeedbackSubmission.user_id)
        .order_by(models.FeedbackSubmission.created_at.desc())
        .limit(limit)
    )
    return AdminFeedbackResponse(
        total=total,
        items=[
            AdminFeedbackRow(
                id=feedback.id,
                message=feedback.message,
                user_id=feedback.user_id,
                user_email=email,
                display_name=display_name,
                created_at=feedback.created_at,
            )
            for feedback, email, display_name in result.all()
        ],
    )


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
                SELECT
                    COUNT(DISTINCT session_id) FILTER (
                        WHERE event_name = 'page_view' AND path = '/'
                    ) AS map_sessions,
                    COUNT(DISTINCT session_id) FILTER (
                        WHERE event_name = 'site_detail_viewed'
                    ) AS site_detail_sessions,
                    COUNT(DISTINCT session_id) FILTER (
                        WHERE event_name = 'trip_plan_submitted'
                    ) AS submitted_sessions,
                    COUNT(DISTINCT session_id) FILTER (
                        WHERE event_name = 'trip_plan_results_viewed'
                    ) AS results_sessions,
                    COUNT(DISTINCT session_id) FILTER (
                        WHERE event_name = 'trip_plan_site_opened'
                    ) AS opened_site_sessions
                FROM product_events
                WHERE created_at >= :cutoff
                """
            ),
            {"cutoff": cutoff},
        )
    ).mappings().one()
    map_sessions = int(engagement_row["map_sessions"] or 0)
    site_detail_sessions = int(engagement_row["site_detail_sessions"] or 0)
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
        map_to_site_rate=_rate(site_detail_sessions, map_sessions),
        daily=daily,
        event_counts=event_counts,
        top_paths=top_paths,
        trip_planner=AnalyticsFunnel(
            submitted_sessions=submitted_sessions,
            results_sessions=results_sessions,
            opened_site_sessions=opened_site_sessions,
            results_rate=_rate(results_sessions, submitted_sessions),
            site_open_rate=_rate(opened_site_sessions, results_sessions),
        ),
        recommendation_feedback=recommendation_feedback,
        top_sites=top_sites,
    )


@router.get("/forecast-runs", response_model=List[ForecastRunSummary])
async def list_forecast_runs(
    limit: int = Query(default=20, ge=1, le=100),
    _: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total_sites = int((await db.execute(select(func.count(models.Site.site_id)))).scalar_one() or 0)
    result = await db.execute(
        select(
            models.Prediction.gfs_forecast_at,
            func.min(models.Prediction.computed_at),
            func.max(models.Prediction.computed_at),
            func.count(func.distinct(models.Prediction.site_id)),
            func.count(),
            func.min(models.Prediction.date),
            func.max(models.Prediction.date),
        )
        .group_by(models.Prediction.gfs_forecast_at)
        .order_by(models.Prediction.gfs_forecast_at.desc())
        .limit(limit)
    )

    runs = []
    for row in result.all():
        covered_sites = int(row[3] or 0)
        coverage = _coverage_percent(covered_sites, total_sites)
        runs.append(
            ForecastRunSummary(
                gfs_forecast_at=row[0],
                computed_at=row[1],
                completed_at=row[2],
                covered_sites=covered_sites,
                expected_sites=total_sites,
                coverage_percent=coverage,
                prediction_rows=int(row[4] or 0),
                forecast_start_date=row[5].isoformat(),
                forecast_end_date=row[6].isoformat(),
                status="complete" if covered_sites >= total_sites and total_sites > 0 else "partial",
            )
        )
    return runs


@router.post("/forecast/check", response_model=AdminOperation, status_code=status.HTTP_202_ACCEPTED)
async def trigger_forecast_check(_: models.User = Depends(require_admin)):
    task = celery.send_task("app.celery_app.check_and_trigger_forecast_processing")
    return AdminOperation(operation="check_and_trigger_forecast_processing", task_id=task.id)


async def _site_rows(
    db: AsyncSession,
    *,
    offset: int = 0,
    limit: int = 500,
    site_id: Optional[int] = None,
):
    latest_prediction = (
        select(
            models.Prediction.site_id.label("site_id"),
            func.max(models.Prediction.gfs_forecast_at).label("latest_gfs_forecast_at"),
        )
        .group_by(models.Prediction.site_id)
        .subquery()
    )
    query = (
        select(
            models.Site,
            models.SiteInfo.country,
            models.SiteInfo.html,
            latest_prediction.c.latest_gfs_forecast_at,
        )
        .outerjoin(models.SiteInfo, models.SiteInfo.site_id == models.Site.site_id)
        .outerjoin(latest_prediction, latest_prediction.c.site_id == models.Site.site_id)
        .order_by(models.Site.name.asc())
    )
    if site_id is not None:
        query = query.where(models.Site.site_id == site_id)
    else:
        query = query.offset(offset).limit(limit)
    return (await db.execute(query)).all()


async def _serialize_sites(db: AsyncSession, rows) -> List[AdminSite]:
    site_ids = [row[0].site_id for row in rows]
    tags_by_site = await crud.get_tags_by_site_ids(db, site_ids)
    return [
        AdminSite(
            site_id=site.site_id,
            name=site.name,
            latitude=site.latitude,
            longitude=site.longitude,
            altitude=site.altitude,
            lat_gfs=site.lat_gfs,
            lon_gfs=site.lon_gfs,
            country=country,
            html=html,
            tags=tags_by_site.get(site.site_id, []),
            latest_gfs_forecast_at=latest_cycle,
        )
        for site, country, html, latest_cycle in rows
    ]


@router.get("/sites", response_model=List[AdminSite])
async def list_sites(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=500, ge=1, le=1000),
    _: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await _serialize_sites(db, await _site_rows(db, offset=offset, limit=limit))


@router.patch("/sites/{site_id}", response_model=AdminSite)
async def update_site(
    site_id: int,
    payload: AdminSiteUpdate,
    _: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    site = await db.get(models.Site, site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")

    updates = payload.model_dump(exclude_unset=True)
    tags = updates.pop("tags", None)
    country_supplied = "country" in updates
    html_supplied = "html" in updates
    country = updates.pop("country", None)
    html = updates.pop("html", None)

    for field, value in updates.items():
        setattr(site, field, value)

    info = await db.get(models.SiteInfo, site_id)
    if country_supplied or html_supplied:
        if info is None:
            info = models.SiteInfo(
                site_id=site_id,
                site_name=site.name,
                country=country or "Unknown",
                html=html or "",
            )
            db.add(info)
        else:
            info.site_name = site.name
            if country_supplied:
                info.country = country or "Unknown"
            if html_supplied:
                info.html = html or ""

    if tags is not None:
        normalized_tags = sorted({tag.strip() for tag in tags if tag.strip()})
        await db.execute(delete(models.SiteTag).where(models.SiteTag.site_id == site_id))
        for tag in normalized_tags:
            db.add(models.SiteTag(site_id=site_id, tag=tag))

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Site update conflicts with existing data") from exc

    rows = await _site_rows(db, site_id=site_id)
    return (await _serialize_sites(db, rows))[0]


@router.get("/resources", response_model=AdminResourcePage)
async def list_resources(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=250),
    missing_only: bool = False,
    _: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    all_sites = (await db.execute(select(models.Site).order_by(models.Site.name.asc()))).scalars().all()
    items: List[AdminResourceSite] = []

    for site in all_sites:
        try:
            resource = await crud.get_site_resources(db, site.site_id)
        except SQLAlchemyError:
            await db.rollback()
            logger.info("Resources unavailable for site_id=%s", site.site_id, exc_info=True)
            resource = None

        links = resource.local_resources if resource else []
        webcam_urls = resource.webcam_urls if resource else []
        meteostation_urls = resource.meteostation_urls if resource else []
        if missing_only and (links or webcam_urls or meteostation_urls):
            continue
        items.append(
            AdminResourceSite(
                site_id=site.site_id,
                site_name=site.name,
                source_run_id=resource.source_run_id if resource else None,
                run_extracted_at=resource.run_extracted_at if resource else None,
                resources=[AdminResourceLink.model_validate(link, from_attributes=True) for link in links],
                webcam_urls=webcam_urls,
                meteostation_urls=meteostation_urls,
            )
        )

    total = len(items)
    return AdminResourcePage(items=items[offset : offset + limit], total=total, offset=offset, limit=limit)
