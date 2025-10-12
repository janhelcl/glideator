from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from .push_delivery import (
    PushConfigError,
    PushDeliveryError,
    VapidConfig,
    get_vapid_configuration,
    send_web_push,
)


COMPARISON_OPERATORS = {
    "gt": lambda value, threshold: value > threshold,
    "gte": lambda value, threshold: value >= threshold,
    "lt": lambda value, threshold: value < threshold,
    "lte": lambda value, threshold: value <= threshold,
    "eq": lambda value, threshold: value == threshold,
}


def ensure_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@dataclass
class NotificationTrigger:
    notification: models.UserNotification
    prediction: models.Prediction
    payload: Dict


def _build_notification_payload(
    notification: models.UserNotification,
    prediction: models.Prediction,
    site_names: Dict[int, str],
    now: datetime,
) -> Dict:
    computed_at = ensure_aware(prediction.computed_at)
    forecast_at = ensure_aware(prediction.gfs_forecast_at)

    return {
        "notification_id": notification.notification_id,
        "site_id": notification.site_id,
        "site_name": site_names.get(notification.site_id, "Your site"),
        "metric": notification.metric,
        "comparison": notification.comparison,
        "threshold": notification.threshold,
        "value": round(prediction.value * 100, 1),
        "prediction_date": prediction.date.isoformat(),
        "computed_at": computed_at.isoformat() if computed_at else None,
        "gfs_forecast_at": forecast_at.isoformat() if forecast_at else None,
        "lead_time_hours": notification.lead_time_hours,
        "triggered_at": now.isoformat(),
    }


def _build_notification_title(payload: Dict) -> str:
    site_name = payload.get("site_name") or "Glideator site"
    return f"Heads up for {site_name}!"


def _build_notification_body(payload: Dict) -> str:
    prediction_date = payload.get("prediction_date")
    value = payload.get("value")
    metric = payload.get("metric")
    lead_time_hours = payload.get("lead_time_hours", 0)

    today_iso = datetime.utcnow().date().isoformat()
    if prediction_date == today_iso:
        day_phrase = "today"
    else:
        day_phrase = prediction_date

    return (
        f"Looks like {day_phrase} is {value}% flyable — above your {metric} goal. "
        f"We’re letting you know {lead_time_hours} hours early so you can plan it in."
    )


async def evaluate_and_queue_notifications(
    db: AsyncSession,
    now: Optional[datetime] = None,
) -> List[models.NotificationEvent]:
    now = ensure_aware(now or datetime.now(timezone.utc))

    result = await db.execute(
        select(models.UserNotification).where(models.UserNotification.active.is_(True))
    )
    notifications: List[models.UserNotification] = result.scalars().all()
    if not notifications:
        return []

    site_ids = {n.site_id for n in notifications}
    user_ids = {n.user_id for n in notifications}
    metrics = {n.metric for n in notifications}
    max_lead_hours = max((n.lead_time_hours for n in notifications), default=0)

    start_date = now.date()
    day_window = max(0, (max_lead_hours + 23) // 24)
    end_date = start_date + timedelta(days=day_window)

    predictions_result = await db.execute(
        select(models.Prediction).where(
            models.Prediction.site_id.in_(site_ids),
            models.Prediction.metric.in_(metrics),
            models.Prediction.date >= start_date,
            models.Prediction.date <= end_date,
        )
    )
    predictions = predictions_result.scalars().all()
    if not predictions:
        return []

    predictions_by_key: Dict[Tuple[int, str], List[models.Prediction]] = defaultdict(list)
    for pred in predictions:
        predictions_by_key[(pred.site_id, pred.metric)].append(pred)

    for preds in predictions_by_key.values():
        preds.sort(key=lambda p: (p.date, p.computed_at))

    site_result = await db.execute(
        select(models.Site.site_id, models.Site.name).where(models.Site.site_id.in_(site_ids))
    )
    site_names = {row.site_id: row.name for row in site_result}

    subs_result = await db.execute(
        select(models.PushSubscription).where(
            models.PushSubscription.user_id.in_(user_ids),
            models.PushSubscription.is_active.is_(True),
        )
    )
    subscriptions_by_user: Dict[int, List[models.PushSubscription]] = defaultdict(list)
    for sub in subs_result.scalars().all():
        subscriptions_by_user[sub.user_id].append(sub)

    triggers: List[NotificationTrigger] = []

    for notification in notifications:
        key = (notification.site_id, notification.metric)
        preds = predictions_by_key.get(key, [])
        if not preds:
            continue

        window_end = now + timedelta(hours=notification.lead_time_hours)
        last_triggered = ensure_aware(notification.last_triggered_at)

        for pred in preds:
            if pred.date < start_date:
                continue
            if notification.lead_time_hours > 0 and pred.date > window_end.date():
                continue

            computed_at = ensure_aware(pred.computed_at)
            if last_triggered and computed_at and last_triggered >= computed_at:
                continue

            comparator = COMPARISON_OPERATORS.get(notification.comparison)
            if not comparator:
                continue

            normalized_threshold = notification.threshold / 100.0
            if comparator(pred.value, normalized_threshold):
                payload = _build_notification_payload(notification, pred, site_names, now)
                triggers.append(
                    NotificationTrigger(notification=notification, prediction=pred, payload=payload)
                )
                break

    if not triggers:
        return []

    events: List[models.NotificationEvent] = []
    for trigger in triggers:
        notification = trigger.notification
        subscriptions = subscriptions_by_user.get(notification.user_id, [])

        if not subscriptions:
            event = models.NotificationEvent(
                notification_id=notification.notification_id,
                subscription_id=None,
                payload=trigger.payload,
                delivery_status="queued",
            )
            db.add(event)
            await db.flush()
            events.append(event)
        else:
            for subscription in subscriptions:
                subscription.last_used_at = now
                event = models.NotificationEvent(
                    notification_id=notification.notification_id,
                    subscription_id=subscription.subscription_id,
                    payload=trigger.payload,
                    delivery_status="queued",
                    subscription=subscription,
                )
                db.add(event)
                await db.flush()
                events.append(event)

        notification.last_triggered_at = now

    await db.commit()
    for event in events:
        await db.refresh(event)

    vapid_config: Optional[VapidConfig] = None
    try:
        vapid_config = get_vapid_configuration()
    except PushConfigError:
        pass

    for event in events:
        if event.subscription_id is None:
            event.delivery_status = "skipped"
            continue

        if not vapid_config:
            event.delivery_status = "config_missing"
            continue

        try:
            if not event.subscription:
                event.subscription = await db.get(models.PushSubscription, event.subscription_id)
            if not event.subscription:
                event.delivery_status = "missing_subscription"
                continue

            title = _build_notification_title(event.payload)
            body = _build_notification_body(event.payload)

            await send_web_push(
                event.subscription,
                {"title": title, "body": body, "data": event.payload},
                vapid_config,
            )
            event.delivery_status = "sent"
        except PushDeliveryError:
            event.delivery_status = "failed"
        except Exception:
            event.delivery_status = "failed"

    await db.commit()
    for event in events:
        await db.refresh(event)

    return events
