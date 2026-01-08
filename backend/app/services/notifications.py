"""
Notification evaluation engine.

Evaluates user notification rules against weather predictions and sends
push notifications when conditions are met.

Timing context: GFS weather forecasts update 4 times daily at approximately
00:00, 06:00, 12:00, and 18:00 UTC. The exact arrival time varies, so this
service runs every 30 minutes (via Celery Beat) to catch updates promptly.

Key concepts:
- NotifiedForecast: Tracks state per (notification, forecast_date) to prevent
  duplicate notifications and detect forecast evolution
- Event types:
  - initial: First time threshold is met for a forecast date
  - deteriorated: Was above threshold, now below
  - improved: Currently above threshold AND improvement >= improvement_threshold
- improvement_threshold: Minimum change (default 15%) to trigger "improved"
  notification, preventing spam from minor forecast fluctuations

See also: docs/adr/001-notification-system.md
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from .. import crud
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

EVENT_TYPE_INITIAL = "initial"
EVENT_TYPE_DETERIORATED = "deteriorated"
EVENT_TYPE_IMPROVED = "improved"


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
    event_type: str
    previous_value: Optional[float] = None


def _build_notification_payload(
    notification: models.UserNotification,
    prediction: models.Prediction,
    site_names: Dict[int, str],
    now: datetime,
    event_type: str,
    previous_value: Optional[float] = None,
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
        "previous_value": round(previous_value * 100, 1) if previous_value is not None else None,
        "prediction_date": prediction.date.isoformat(),
        "computed_at": computed_at.isoformat() if computed_at else None,
        "gfs_forecast_at": forecast_at.isoformat() if forecast_at else None,
        "lead_time_hours": notification.lead_time_hours,
        "triggered_at": now.isoformat(),
        "event_type": event_type,
    }


def _build_notification_title(payload: Dict) -> str:
    site_name = payload.get("site_name") or "Glideator site"
    event_type = payload.get("event_type", EVENT_TYPE_INITIAL)

    if event_type == EVENT_TYPE_DETERIORATED:
        return f"Conditions changed at {site_name}"
    elif event_type == EVENT_TYPE_IMPROVED:
        return f"Good news for {site_name}!"
    else:
        return f"Heads up for {site_name}!"


def _build_notification_body(payload: Dict) -> str:
    prediction_date = payload.get("prediction_date")
    value = payload.get("value")
    previous_value = payload.get("previous_value")
    metric = payload.get("metric")
    lead_time_hours = payload.get("lead_time_hours", 0)
    event_type = payload.get("event_type", EVENT_TYPE_INITIAL)

    today_iso = datetime.utcnow().date().isoformat()
    if prediction_date == today_iso:
        day_phrase = "today"
    else:
        day_phrase = prediction_date

    if event_type == EVENT_TYPE_DETERIORATED:
        return (
            f"Heads up: {day_phrase} dropped from {previous_value}% to {value}% — "
            f"now below your {metric} threshold. You may want to reconsider your plans."
        )
    elif event_type == EVENT_TYPE_IMPROVED:
        return (
            f"Update: {day_phrase} improved from {previous_value}% to {value}% — "
            f"looking even better for flying!"
        )
    else:
        return (
            f"Looks like {day_phrase} is {value}% flyable — above your {metric} goal. "
            f"We're letting you know {lead_time_hours} hours early so you can plan it in."
        )


async def evaluate_and_queue_notifications(
    db: AsyncSession,
    now: Optional[datetime] = None,
) -> List[models.NotificationEvent]:
    now = ensure_aware(now or datetime.now(timezone.utc))

    # Fetch all active notifications
    result = await db.execute(
        select(models.UserNotification).where(models.UserNotification.active.is_(True))
    )
    notifications: List[models.UserNotification] = result.scalars().all()
    if not notifications:
        return []

    site_ids = {n.site_id for n in notifications}
    user_ids = {n.user_id for n in notifications}
    metrics = {n.metric for n in notifications}
    notification_ids = [n.notification_id for n in notifications]
    max_lead_hours = max((n.lead_time_hours for n in notifications), default=0)

    start_date = now.date()
    day_window = max(0, (max_lead_hours + 23) // 24)
    end_date = start_date + timedelta(days=day_window)

    # Fetch predictions
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

    # Fetch site names
    site_result = await db.execute(
        select(models.Site.site_id, models.Site.name).where(models.Site.site_id.in_(site_ids))
    )
    site_names = {row.site_id: row.name for row in site_result}

    # Fetch push subscriptions
    subs_result = await db.execute(
        select(models.PushSubscription).where(
            models.PushSubscription.user_id.in_(user_ids),
            models.PushSubscription.is_active.is_(True),
        )
    )
    subscriptions_by_user: Dict[int, List[models.PushSubscription]] = defaultdict(list)
    for sub in subs_result.scalars().all():
        subscriptions_by_user[sub.user_id].append(sub)

    # Fetch existing notified_forecasts records
    notified_forecasts = await crud.get_notified_forecasts_for_notifications(
        db, notification_ids, start_date, end_date
    )

    triggers: List[NotificationTrigger] = []

    for notification in notifications:
        key = (notification.site_id, notification.metric)
        preds = predictions_by_key.get(key, [])
        if not preds:
            continue

        window_end = now + timedelta(hours=notification.lead_time_hours)
        normalized_threshold = notification.threshold / 100.0
        improvement_threshold = notification.improvement_threshold / 100.0
        deterioration_threshold = notification.deterioration_threshold / 100.0

        comparator = COMPARISON_OPERATORS.get(notification.comparison)
        if not comparator:
            continue

        for pred in preds:
            if pred.date < start_date:
                continue
            if notification.lead_time_hours > 0 and pred.date > window_end.date():
                continue

            current_value = pred.value
            threshold_met = comparator(current_value, normalized_threshold)

            # Check if we have a previous notification for this forecast date
            nf_key = (notification.notification_id, pred.date)
            notified_forecast = notified_forecasts.get(nf_key)

            event_type = None
            previous_value = None

            if notified_forecast is None:
                # No previous notification for this forecast date
                if threshold_met:
                    event_type = EVENT_TYPE_INITIAL
            else:
                # We have previously notified for this forecast date
                previous_value = notified_forecast.last_value
                was_above_threshold = comparator(previous_value, normalized_threshold)

                if was_above_threshold and not threshold_met:
                    # Crossed below threshold - always notify
                    event_type = EVENT_TYPE_DETERIORATED
                elif not was_above_threshold and not threshold_met:
                    # Was already below threshold, still below - only notify if significant drop
                    if (previous_value - current_value) >= deterioration_threshold:
                        event_type = EVENT_TYPE_DETERIORATED
                elif threshold_met and (current_value - previous_value) >= improvement_threshold:
                    # Conditions improved significantly
                    event_type = EVENT_TYPE_IMPROVED

            if event_type:
                payload = _build_notification_payload(
                    notification, pred, site_names, now, event_type, previous_value
                )
                triggers.append(
                    NotificationTrigger(
                        notification=notification,
                        prediction=pred,
                        payload=payload,
                        event_type=event_type,
                        previous_value=previous_value,
                    )
                )

    if not triggers:
        return []

    # Create events and update notified_forecasts
    events: List[models.NotificationEvent] = []
    for trigger in triggers:
        notification = trigger.notification
        subscriptions = subscriptions_by_user.get(notification.user_id, [])

        # Update notified_forecasts record
        await crud.upsert_notified_forecast(
            db,
            notification.notification_id,
            trigger.prediction.date,
            trigger.prediction.value,
            trigger.event_type,
            now,
        )

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

        # Update last_triggered_at on the notification rule
        notification.last_triggered_at = now

    await db.commit()
    for event in events:
        await db.refresh(event)

    # Attempt push delivery
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
