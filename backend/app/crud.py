from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, with_loader_criteria
from sqlalchemy import and_, func, select, delete
from sqlalchemy.exc import IntegrityError
from collections import defaultdict
from . import models, schemas
from typing import Optional, List, Dict
from datetime import date, datetime, timezone

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
            site_id=site.site_id,
            predictions=predictions_list,
            tags=site_tags[site.site_id]  # Get tags from batch-loaded dict
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
        .where(models.PushSubscription.user_id == user_id)
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
