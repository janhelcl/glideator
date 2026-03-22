import json
import logging
import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, with_loader_criteria
from sqlalchemy import and_, bindparam, func, select, delete, text
from sqlalchemy.exc import IntegrityError
from collections import defaultdict
from . import models, schemas
from typing import Any, Dict, List, Optional, Sequence
from datetime import date, datetime, timezone

logger = logging.getLogger(__name__)

# Populated when SITE_RESOURCES_JSON_PATH is used (see _site_resources_json_index).
_site_resources_json_cache_path: Optional[str] = None
_site_resources_json_cache_mtime: Optional[float] = None
_site_resources_json_cache_index: Optional[Dict[int, dict]] = None


def invalidate_site_resources_json_cache() -> None:
    """Clear JSON file cache (e.g. in tests after changing env or file)."""
    global _site_resources_json_cache_path, _site_resources_json_cache_mtime, _site_resources_json_cache_index
    _site_resources_json_cache_path = None
    _site_resources_json_cache_mtime = None
    _site_resources_json_cache_index = None


def _site_resources_json_file_path() -> Optional[Path]:
    """Resolve JSON path: explicit env, else bundled app/data (same tree as flight_stats.csv).

    Set SITE_RESOURCES_FROM_APP_DATA=false to skip the default file (e.g. in tests).
    """
    raw = os.getenv("SITE_RESOURCES_JSON_PATH", "").strip()
    if raw:
        return Path(raw)
    use_bundled = os.getenv("SITE_RESOURCES_FROM_APP_DATA", "true").lower() not in (
        "0",
        "false",
        "no",
    )
    if not use_bundled:
        return None
    default = Path(__file__).resolve().parent / "data" / "site_resources.json"
    if default.is_file():
        return default
    return None


def _site_resources_json_index() -> Optional[Dict[int, dict]]:
    """If a JSON file path is configured and exists, return site_id -> row; None = use DB instead."""
    global _site_resources_json_cache_path, _site_resources_json_cache_mtime, _site_resources_json_cache_index
    path = _site_resources_json_file_path()
    if path is None:
        return None
    if not path.is_file():
        logger.warning("Site resources JSON path is not a file: %s", path)
        return {}

    try:
        mtime = path.stat().st_mtime
    except OSError as e:
        logger.warning("Site resources JSON stat failed: %s", e)
        return {}

    if (
        _site_resources_json_cache_index is not None
        and _site_resources_json_cache_path == str(path.resolve())
        and _site_resources_json_cache_mtime == mtime
    ):
        return _site_resources_json_cache_index

    try:
        with path.open(encoding="utf-8") as f:
            payload = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load site resources JSON %s: %s", path, e)
        _site_resources_json_cache_path = str(path.resolve())
        _site_resources_json_cache_mtime = mtime
        _site_resources_json_cache_index = {}
        return _site_resources_json_cache_index

    if not isinstance(payload, list):
        logger.error("Site resources JSON must be a JSON array of site objects, got %s", type(payload))
        _site_resources_json_cache_index = {}
        return _site_resources_json_cache_index

    index: Dict[int, dict] = {}
    for row in payload:
        if not isinstance(row, dict) or "site_id" not in row:
            continue
        try:
            index[int(row["site_id"])] = row
        except (TypeError, ValueError):
            continue

    _site_resources_json_cache_path = str(path.resolve())
    _site_resources_json_cache_mtime = mtime
    _site_resources_json_cache_index = index
    logger.info("Loaded %d site resource record(s) from %s", len(index), path)
    return _site_resources_json_cache_index

async def get_site(db: AsyncSession, site_id: int):
    result = await db.execute(select(models.Site).filter(models.Site.site_id == site_id))
    return result.scalar_one_or_none()

async def get_site_by_name(db: AsyncSession, name: str):
    result = await db.execute(select(models.Site).filter(models.Site.name == name))
    return result.scalar_one_or_none()

async def get_sites(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100, 
    metric: Optional[str] = None, 
    date: Optional[date] = None
):
    query = select(models.Site)
    
    if metric and date:
        query = query.options(
            with_loader_criteria(models.Prediction, 
                                 and_(
                                     models.Prediction.metric == metric,
                                     models.Prediction.date == date
                                 ), 
                                 include_aliases=True)
        ).options(selectinload(models.Site.predictions))
        
        query = query.join(models.Site.predictions).filter(
            and_(
                models.Prediction.metric == metric,
                models.Prediction.date == date
            )
        ).distinct()
    
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

async def get_site_list(db: AsyncSession):
    """
    Retrieves a list of all sites with their IDs and names.
    """
    result = await db.execute(select(models.Site.site_id, models.Site.name))
    return result.all()

async def get_tags_by_site_id(db: AsyncSession, site_id: int) -> List[str]:
    result = await db.execute(select(models.SiteTag).filter(models.SiteTag.site_id == site_id))
    return [row.tag for row in result.scalars().all()]

async def get_tags_by_site_ids(db: AsyncSession, site_ids: List[int]) -> Dict[int, List[str]]:
    """
    Bulk load tags for multiple sites to avoid N+1 query problem.
    Returns a dictionary mapping site_id to list of tags.
    """
    if not site_ids:
        return {}
    
    result = await db.execute(
        select(models.SiteTag).filter(models.SiteTag.site_id.in_(site_ids))
    )
    all_tags = result.scalars().all()
    
    # Group tags by site_id
    site_tags = defaultdict(list)
    for tag in all_tags:
        site_tags[tag.site_id].append(tag.tag)
    
    return dict(site_tags)

async def replace_site_tags(db: AsyncSession, site_id: int, tags: List[str]):
    await db.execute(delete(models.SiteTag).where(models.SiteTag.site_id == site_id))
    for t in tags:
        db_tag = models.SiteTag(site_id=site_id, tag=t)
        db.add(db_tag)
    await db.commit()

def replace_site_tags_sync(db, site_id: int, tags: List[str]):
    """Synchronous version for data loading during startup"""
    db.query(models.SiteTag).filter(models.SiteTag.site_id == site_id).delete()
    for t in tags:
        db_tag = models.SiteTag(site_id=site_id, tag=t)
        db.add(db_tag)
    db.commit()

async def get_all_unique_tags(db: AsyncSession) -> List[str]:
    """Return all unique tag strings across sites."""
    result = await db.execute(select(models.SiteTag.tag).distinct().order_by(models.SiteTag.tag.asc()))
    return [row[0] for row in result.all()]

async def get_tags_with_min_sites(db: AsyncSession, min_sites: int = 2) -> List[str]:
    """Return tags that are used by at least min_sites distinct sites."""
    q = (
        select(models.SiteTag.tag)
        .group_by(models.SiteTag.tag)
        .having(func.count(func.distinct(models.SiteTag.site_id)) >= min_sites)
        .order_by(models.SiteTag.tag.asc())
    )
    result = await db.execute(q)
    return [row[0] for row in result.all()]

async def get_predictions(db: AsyncSession, site_id: int, query_date: Optional[date] = None, metric: Optional[str] = None):
    """
    Retrieves predictions based on site_id, and optionally filters by date and metric.
    """
    query = select(models.Prediction).filter(models.Prediction.site_id == site_id)
    
    if query_date:
        query = query.filter(models.Prediction.date == query_date)
    
    if metric:
        query = query.filter(models.Prediction.metric == metric)
    
    result = await db.execute(query)
    return result.scalars().all()

async def create_prediction(db: AsyncSession, prediction: schemas.PredictionCreate):
    db_prediction = models.Prediction(**prediction.dict())
    db.add(db_prediction)
    await db.commit()
    await db.refresh(db_prediction)
    return db_prediction

async def get_latest_gfs_forecast(db: AsyncSession) -> Optional[datetime]:
    """
    Retrieves the latest gfs_forecast_at timestamp from predictions.
    """
    result = await db.execute(select(func.max(models.Prediction.gfs_forecast_at)))
    return result.scalar_one_or_none()

async def create_forecast(db: AsyncSession, forecast: schemas.ForecastCreate):
    db_forecast = models.Forecast(**forecast.dict())
    db.add(db_forecast)
    await db.commit()
    await db.refresh(db_forecast)
    return db_forecast

async def get_forecasts_by_date(db: AsyncSession, query_date: date) -> List[models.Forecast]:
    result = await db.execute(select(models.Forecast).filter(models.Forecast.date == query_date))
    return result.scalars().all()

async def get_forecast(db: AsyncSession, query_date: date, lat_gfs: float, lon_gfs: float) -> Optional[models.Forecast]:
    result = await db.execute(select(models.Forecast).filter(
        models.Forecast.date == query_date,
        models.Forecast.lat_gfs == lat_gfs,
        models.Forecast.lon_gfs == lon_gfs
    ))
    return result.scalar_one_or_none()

async def delete_forecasts_by_date(db: AsyncSession, query_date: date):
    await db.execute(delete(models.Forecast).where(models.Forecast.date == query_date))
    await db.commit()

async def get_sites_with_predictions(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(models.Site).offset(skip).limit(limit))
    sites = result.scalars().all()
    site_ids = [site.site_id for site in sites]
    
    site_predictions = defaultdict(lambda: defaultdict(dict))  # Changed to dict instead of list

    predictions_result = await db.execute(
        select(models.Prediction)
        .filter(models.Prediction.site_id.in_(site_ids))
        .order_by(models.Prediction.date, models.Prediction.metric)
    )
    predictions = predictions_result.scalars().all()

    # Store predictions by site_id and date
    for pred in predictions:
        if pred.date not in site_predictions[pred.site_id]:
            site_predictions[pred.site_id][pred.date] = {
                'metrics': {},
                'computed_at': pred.computed_at,
                'gfs_forecast_at': pred.gfs_forecast_at
            }
        site_predictions[pred.site_id][pred.date]['metrics'][pred.metric] = pred.value

    # Batch load all tags for all sites in a single query
    tags_result = await db.execute(
        select(models.SiteTag).filter(models.SiteTag.site_id.in_(site_ids))
    )
    all_tags = tags_result.scalars().all()
    
    # Group tags by site_id
    site_tags = defaultdict(list)
    for tag in all_tags:
        site_tags[tag.site_id].append(tag.tag)

    result_list = []
    for site in sites:
        predictions_list = []
        for pred_date in sorted(site_predictions[site.site_id].keys()):
            pred_data = site_predictions[site.site_id][pred_date]
            metrics_dict = pred_data['metrics']
            # Ensure consistent ordering: XC0, XC10, XC20, ..., XC100
            ordered_values = [
                metrics_dict.get(f'XC{i}', 0.0)
                for i in [0] + list(range(10, 101, 10))
            ]
            predictions_list.append(schemas.PredictionValues(
                date=pred_date,
                values=ordered_values,
                computed_at=pred_data['computed_at'],
                gfs_forecast_at=pred_data['gfs_forecast_at']
            ))
        
        site_response = schemas.SiteResponse(
            name=site.name,
            latitude=site.latitude,
            longitude=site.longitude,
            altitude=site.altitude,
            site_id=site.site_id,
            predictions=predictions_list,
            tags=site_tags[site.site_id]
        )
        result_list.append(site_response)

    return result_list

async def get_flight_stats(db: AsyncSession, site_id: int, month: int):
    result = await db.execute(select(models.FlightStats).filter(
        models.FlightStats.site_id == site_id,
        models.FlightStats.month == month
    ))
    return result.scalar_one_or_none()

async def create_flight_stats(db: AsyncSession, flight_stats: schemas.FlightStatsCreate):
    db_flight_stats = models.FlightStats(**flight_stats.dict())
    db.add(db_flight_stats)
    await db.commit()
    await db.refresh(db_flight_stats)
    return db_flight_stats

def create_flight_stats_sync(db, flight_stats: schemas.FlightStatsCreate):
    """Synchronous version for data loading during startup"""
    db_flight_stats = models.FlightStats(**flight_stats.dict())
    db.add(db_flight_stats)
    db.commit()
    db.refresh(db_flight_stats)
    return db_flight_stats

async def get_flight_stats_by_site_id(db: AsyncSession, site_id: int):
    result = await db.execute(select(models.FlightStats).filter(
        models.FlightStats.site_id == site_id
    ).order_by(models.FlightStats.month))
    return result.scalars().all()

async def get_spot(db: AsyncSession, spot_id: int):
    result = await db.execute(select(models.Spot).filter(models.Spot.spot_id == spot_id))
    return result.scalar_one_or_none()

async def get_spots_by_site_id(db: AsyncSession, site_id: int):
    result = await db.execute(select(models.Spot).filter(models.Spot.site_id == site_id))
    return result.scalars().all()

async def create_spot(db: AsyncSession, spot: schemas.SpotCreate):
    db_spot = models.Spot(**spot.dict())
    db.add(db_spot)
    await db.commit()
    await db.refresh(db_spot)
    return db_spot

def create_spot_sync(db, spot: schemas.SpotCreate):
    """Synchronous version for data loading during startup"""
    db_spot = models.Spot(**spot.dict())
    db.add(db_spot)
    db.commit()
    db.refresh(db_spot)
    return db_spot

async def create_site_info(db: AsyncSession, site_info: schemas.SiteInfoCreate):
    db_site_info = models.SiteInfo(**site_info.dict())
    db.add(db_site_info)
    await db.commit()
    await db.refresh(db_site_info)
    return db_site_info

def create_site_info_sync(db, site_info: schemas.SiteInfoCreate):
    """Synchronous version for data loading during startup"""
    db_site_info = models.SiteInfo(**site_info.dict())
    db.add(db_site_info)
    db.commit()
    db.refresh(db_site_info)
    return db_site_info

async def get_site_info(db: AsyncSession, site_id: int):
    result = await db.execute(select(models.SiteInfo).filter(models.SiteInfo.site_id == site_id))
    return result.scalar_one_or_none()


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


async def get_site_resources(db: AsyncSession, site_id: int) -> schemas.SiteResourcesResponse:
    """Load site resources from glideator_ground_crew or from SITE_RESOURCES_JSON_PATH export."""
    json_index = _site_resources_json_index()
    if json_index is not None:
        row = json_index.get(site_id)
        if not row:
            return schemas.SiteResourcesResponse(site_id=site_id)
        return schemas.SiteResourcesResponse.model_validate(row)

    # Prefer latest run that has ≥1 validated (ok/redirected) candidate; else latest run.
    # Keeps SQL aligned with ground_crew/site_resources_query.py.
    run_result = await db.execute(
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
    )
    run_row = run_result.mappings().first()
    if not run_row:
        run_result = await db.execute(
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
        )
        run_row = run_result.mappings().first()
    if not run_row:
        return schemas.SiteResourcesResponse(site_id=site_id)

    run_id = int(run_row["run_id"])
    run_extracted_at = run_row["extracted_at"]
    if run_extracted_at is not None and not isinstance(run_extracted_at, datetime):
        run_extracted_at = None

    cand_result = await db.execute(
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
    )
    cand_rows = [dict(r) for r in cand_result.mappings().all()]
    candidate_ids = [int(r["candidate_id"]) for r in cand_rows]

    webcam_urls: List[str] = []
    meteostation_urls: List[str] = []
    if candidate_ids:
        webcam_stmt = (
            text(
                """
                SELECT webcam_url, extracted_at
                FROM glideator_ground_crew.webcam_extractions
                WHERE candidate_id IN :cids
                  AND found = true
                  AND NULLIF(TRIM(webcam_url), '') IS NOT NULL
                ORDER BY extracted_at DESC NULLS LAST
                """
            ).bindparams(bindparam("cids", expanding=True))
        )
        webcam_result = await db.execute(webcam_stmt, {"cids": candidate_ids})
        webcam_urls = _dedupe_urls_preserve_order(
            [dict(r) for r in webcam_result.mappings().all()], "webcam_url"
        )

        meteo_stmt = (
            text(
                """
                SELECT meteostation_url, extracted_at
                FROM glideator_ground_crew.meteostation_extractions
                WHERE candidate_id IN :cids
                  AND found = true
                  AND NULLIF(TRIM(meteostation_url), '') IS NOT NULL
                ORDER BY extracted_at DESC NULLS LAST
                """
            ).bindparams(bindparam("cids", expanding=True))
        )
        meteo_result = await db.execute(mete_stmt, {"cids": candidate_ids})
        meteostation_urls = _dedupe_urls_preserve_order(
            [dict(r) for r in meteo_result.mappings().all()], "meteostation_url"
        )

    local_resources = [schemas.SiteResourceLink(**r) for r in cand_rows]

    return schemas.SiteResourcesResponse(
        site_id=site_id,
        source_run_id=run_id,
        run_extracted_at=run_extracted_at,
        local_resources=local_resources,
        webcam_url=webcam_urls[0] if webcam_urls else None,
        webcam_urls=webcam_urls,
        meteostation_url=meteostation_urls[0] if meteostation_urls else None,
        meteostation_urls=meteostation_urls,
    )


async def create_site(db: AsyncSession, site: schemas.SiteBase):
    db_site = models.Site(**site.dict())
    db.add(db_site)
    await db.commit()
    await db.refresh(db_site)
    return db_site

def create_site_sync(db, site: schemas.SiteBase):
    """Synchronous version for data loading during startup"""
    db_site = models.Site(**site.dict())
    db.add(db_site)
    db.commit()
    db.refresh(db_site)
    return db_site

# --- Notification CRUD Functions ---


async def list_user_notifications(db: AsyncSession, user_id: int) -> List[models.UserNotification]:
    result = await db.execute(
        select(models.UserNotification)
        .where(models.UserNotification.user_id == user_id)
        .order_by(models.UserNotification.notification_id)
    )
    return result.scalars().all()


async def get_user_notification(db: AsyncSession, user_id: int, notification_id: int) -> Optional[models.UserNotification]:
    result = await db.execute(
        select(models.UserNotification).where(
            models.UserNotification.user_id == user_id,
            models.UserNotification.notification_id == notification_id,
        )
    )
    return result.scalar_one_or_none()


async def create_user_notification(
    db: AsyncSession,
    user_id: int,
    payload: schemas.NotificationCreate,
) -> models.UserNotification:
    data = payload.model_dump()
    notification = models.UserNotification(
        user_id=user_id,
        site_id=data["site_id"],
        metric=data["metric"],
        comparison=data["comparison"],
        threshold=data["threshold"],
        lead_time_hours=data["lead_time_hours"],
        improvement_threshold=data.get("improvement_threshold", 15.0),
    )
    db.add(notification)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    await db.refresh(notification)
    return notification


async def update_user_notification(
    db: AsyncSession,
    notification: models.UserNotification,
    payload: schemas.NotificationUpdate,
) -> models.UserNotification:
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(notification, field, value)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    await db.refresh(notification)
    return notification


async def delete_user_notification(db: AsyncSession, notification: models.UserNotification) -> None:
    await db.delete(notification)
    await db.commit()


async def get_active_notifications(
    db: AsyncSession,
    site_ids: Optional[List[int]] = None,
    metric: Optional[str] = None,
) -> List[models.UserNotification]:
    query = select(models.UserNotification).where(models.UserNotification.active.is_(True))
    if site_ids:
        query = query.where(models.UserNotification.site_id.in_(site_ids))
    if metric:
        query = query.where(models.UserNotification.metric == metric)
    result = await db.execute(query)
    return result.scalars().all()


async def update_notification_last_triggered(
    db: AsyncSession,
    notification: models.UserNotification,
    triggered_at: datetime,
) -> None:
    notification.last_triggered_at = triggered_at
    await db.commit()


async def list_push_subscriptions(db: AsyncSession, user_id: int) -> List[models.PushSubscription]:
    result = await db.execute(
        select(models.PushSubscription)
        .where(
            models.PushSubscription.user_id == user_id,
            models.PushSubscription.is_active.is_(True)
        )
        .order_by(models.PushSubscription.subscription_id)
    )
    return result.scalars().all()


async def upsert_push_subscription(
    db: AsyncSession,
    user_id: int,
    payload: schemas.PushSubscriptionCreate,
) -> models.PushSubscription:
    data = payload.model_dump()
    result = await db.execute(
        select(models.PushSubscription).where(models.PushSubscription.endpoint == data["endpoint"])
    )
    subscription = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if subscription:
        subscription.user_id = user_id
        subscription.p256dh = data["p256dh"]
        subscription.auth = data["auth"]
        subscription.client_info = data.get("client_info")
        subscription.is_active = True
        subscription.last_used_at = now
    else:
        subscription = models.PushSubscription(
            user_id=user_id,
            endpoint=data["endpoint"],
            p256dh=data["p256dh"],
            auth=data["auth"],
            client_info=data.get("client_info"),
            is_active=True,
            last_used_at=now,
        )
        db.add(subscription)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise
    await db.refresh(subscription)
    return subscription


async def deactivate_push_subscription(
    db: AsyncSession,
    user_id: int,
    subscription_id: int,
) -> Optional[models.PushSubscription]:
    result = await db.execute(
        select(models.PushSubscription).where(
            models.PushSubscription.subscription_id == subscription_id,
            models.PushSubscription.user_id == user_id,
        )
    )
    subscription = result.scalar_one_or_none()
    if not subscription:
        return None
    subscription.is_active = False
    subscription.last_used_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(subscription)
    return subscription


async def get_active_push_subscriptions_for_users(
    db: AsyncSession,
    user_ids: List[int],
) -> Dict[int, List[models.PushSubscription]]:
    if not user_ids:
        return {}
    result = await db.execute(
        select(models.PushSubscription).where(
            models.PushSubscription.user_id.in_(user_ids),
            models.PushSubscription.is_active.is_(True),
        )
    )
    subs = result.scalars().all()
    by_user: Dict[int, List[models.PushSubscription]] = defaultdict(list)
    for sub in subs:
        by_user[sub.user_id].append(sub)
    return by_user


async def create_notification_event(
    db: AsyncSession,
    notification_id: int,
    subscription_id: Optional[int],
    payload: Dict,
    status: str = "queued",
) -> models.NotificationEvent:
    event = models.NotificationEvent(
        notification_id=notification_id,
        subscription_id=subscription_id,
        payload=payload,
        delivery_status=status,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


async def list_notification_events_for_notification(
    db: AsyncSession,
    notification_id: int,
    limit: int = 50,
) -> List[models.NotificationEvent]:
    result = await db.execute(
        select(models.NotificationEvent)
        .where(models.NotificationEvent.notification_id == notification_id)
        .order_by(models.NotificationEvent.triggered_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def list_recent_notification_events_for_user(
    db: AsyncSession,
    user_id: int,
    since: Optional[datetime] = None,
    offset: int = 0,
    limit: int = 50,
) -> List[models.NotificationEvent]:
    """
    Get recent notification events for all of a user's notifications.
    Used for catch-up when app opens after being offline, and for browsing history.

    Args:
        db: Database session
        user_id: The user ID to fetch events for
        since: Only return events triggered after this timestamp
        offset: Number of events to skip for pagination
        limit: Maximum number of events to return
    """
    query = (
        select(models.NotificationEvent)
        .join(models.UserNotification)
        .where(models.UserNotification.user_id == user_id)
    )
    if since:
        query = query.where(models.NotificationEvent.triggered_at > since)
    query = query.order_by(models.NotificationEvent.triggered_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


# --- Notified Forecasts CRUD Functions ---


async def get_notified_forecast(
    db: AsyncSession,
    notification_id: int,
    forecast_date: date,
) -> Optional[models.NotifiedForecast]:
    """Get the notified forecast record for a specific notification and forecast date."""
    result = await db.execute(
        select(models.NotifiedForecast).where(
            models.NotifiedForecast.notification_id == notification_id,
            models.NotifiedForecast.forecast_date == forecast_date,
        )
    )
    return result.scalar_one_or_none()


async def get_notified_forecasts_for_notifications(
    db: AsyncSession,
    notification_ids: List[int],
    start_date: date,
    end_date: date,
) -> Dict[tuple, models.NotifiedForecast]:
    """
    Bulk fetch notified forecasts for multiple notifications and a date range.
    Returns a dict keyed by (notification_id, forecast_date).
    """
    if not notification_ids:
        return {}
    result = await db.execute(
        select(models.NotifiedForecast).where(
            models.NotifiedForecast.notification_id.in_(notification_ids),
            models.NotifiedForecast.forecast_date >= start_date,
            models.NotifiedForecast.forecast_date <= end_date,
        )
    )
    records = result.scalars().all()
    return {(r.notification_id, r.forecast_date): r for r in records}


async def upsert_notified_forecast(
    db: AsyncSession,
    notification_id: int,
    forecast_date: date,
    value: float,
    event_type: str,
    now: Optional[datetime] = None,
) -> models.NotifiedForecast:
    """
    Create or update a notified forecast record.
    Value should be in 0-1 scale (matching prediction.value).
    """
    from sqlalchemy.dialects.postgresql import insert

    now = now or datetime.now(timezone.utc)

    stmt = insert(models.NotifiedForecast).values(
        notification_id=notification_id,
        forecast_date=forecast_date,
        last_value=value,
        last_event_type=event_type,
        notified_at=now,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_notified_forecast_rule_date",
        set_={
            "last_value": stmt.excluded.last_value,
            "last_event_type": stmt.excluded.last_event_type,
            "notified_at": stmt.excluded.notified_at,
        },
    )
    await db.execute(stmt)
    await db.commit()

    # Retrieve the record
    result = await db.execute(
        select(models.NotifiedForecast).where(
            models.NotifiedForecast.notification_id == notification_id,
            models.NotifiedForecast.forecast_date == forecast_date,
        )
    )
    return result.scalar_one()


async def cleanup_old_notified_forecasts(db: AsyncSession, before_date: date) -> int:
    """
    Delete notified_forecasts records where forecast_date is before the given date.
    Returns the number of deleted records.
    """
    result = await db.execute(
        delete(models.NotifiedForecast).where(
            models.NotifiedForecast.forecast_date < before_date
        )
    )
    await db.commit()
    return result.rowcount


# --- Trip Planning CRUD Functions ---

async def get_predictions_for_range(
    db: AsyncSession, 
    start_date: date, 
    end_date: date, 
    site_ids: Optional[List[int]] = None,
    metric: Optional[str] = None
) -> List[models.Prediction]:
    """
    Retrieves predictions for a specific metric within a given date range for all sites.
    
    NOTE: This currently fetches predictions based on the 'metric' column.
    If the schema changes to have XC0, XC50 etc as direct columns, this needs adjustment.
    """
    query = select(models.Prediction).filter(
        models.Prediction.date >= start_date,
        models.Prediction.date <= end_date
    )
    
    if site_ids:
        query = query.filter(models.Prediction.site_id.in_(site_ids))
    
    if metric:
        query = query.filter(models.Prediction.metric == metric)
    
    result = await db.execute(query)
    return result.scalars().all()

async def get_sites_by_ids(db: AsyncSession, site_ids: List[int]) -> List[models.Site]:
    """
    Retrieves site details (specifically ID and name) for a list of site IDs.
    """
    if not site_ids:
        return []
    result = await db.execute(select(models.Site).filter(models.Site.site_id.in_(site_ids)))
    return result.scalars().all()

async def get_all_flight_stats(db: AsyncSession) -> List[models.FlightStats]:
    """
    Retrieves all flight statistics for all sites.
    """
    result = await db.execute(select(models.FlightStats))
    return result.scalars().all()


# --- D2D Similar Dates CRUD Functions ---

async def delete_similar_dates_by_forecast_date(db: AsyncSession, forecast_date: date):
    """
    Delete existing similar_dates for a forecast_date (overwrite behavior).
    """
    await db.execute(delete(models.SimilarDate).where(models.SimilarDate.forecast_date == forecast_date))
    await db.commit()


async def create_similar_date(db: AsyncSession, similar_date: schemas.SimilarDateCreate):
    """
    Upsert a similar_date record (insert or update on conflict).
    """
    from sqlalchemy.dialects.postgresql import insert
    
    data = similar_date.dict()
    stmt = insert(models.SimilarDate).values(**data)
    
    # Build update dict using excluded references
    # stmt.excluded provides access to the EXCLUDED columns
    excluded = stmt.excluded
    stmt = stmt.on_conflict_do_update(
        constraint='similar_dates_pkey',
        set_={
            'similarity': excluded.similarity,
            'forecast_9': excluded.forecast_9,
            'forecast_12': excluded.forecast_12,
            'forecast_15': excluded.forecast_15,
            'computed_at': excluded.computed_at,
            'gfs_forecast_at': excluded.gfs_forecast_at
        }
    )
    await db.execute(stmt)
    await db.commit()
    
    # Retrieve the record
    result = await db.execute(
        select(models.SimilarDate).where(
            models.SimilarDate.site_id == data['site_id'],
            models.SimilarDate.forecast_date == data['forecast_date'],
            models.SimilarDate.past_date == data['past_date']
        )
    )
    return result.scalar_one()


async def get_similar_dates(
    db: AsyncSession,
    site_id: int,
    forecast_date: date
) -> List[models.SimilarDate]:
    """
    Get similar dates for site_id and forecast_date, ordered by similarity (highest first).
    """
    query = select(models.SimilarDate).where(
        models.SimilarDate.site_id == site_id,
        models.SimilarDate.forecast_date == forecast_date
    ).order_by(models.SimilarDate.similarity.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def get_past_date_forecast(
    db: AsyncSession,
    site_id: int,
    forecast_date: date,
    past_date: date
) -> Optional[models.SimilarDate]:
    """
    Get forecast for specific site_id, forecast_date, and past_date from similar_dates table.
    """
    query = select(models.SimilarDate).where(
        models.SimilarDate.site_id == site_id,
        models.SimilarDate.forecast_date == forecast_date,
        models.SimilarDate.past_date == past_date
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()