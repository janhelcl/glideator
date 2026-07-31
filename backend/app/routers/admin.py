import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, models
from ..celery_client import celery
from ..database import AsyncSessionLocal
from ..security import decode_token, is_admin_identity

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
