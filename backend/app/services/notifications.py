import logging
import math
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

logger = logging.getLogger(__name__)


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


async def evaluate_and_queue_notifications(
    db: AsyncSession,
    now: Optional[datetime] = None,
) -> List[models.NotificationEvent]:
    now = ensure_aware(now or datetime.now(timezone.utc))
    logger.info("Starting notification evaluation at %s", now.isoformat())

    result = await db.execute(
        select(models.UserNotification).where(models.UserNotification.active.is_(True))
    )
    notifications: List[models.UserNotification] = result.scalars().all()

    if not notifications:
        logger.info("No active notification rules found")
        return []

    logger.info("Found %d active notification rules", len(notifications))
    for n in notifications:
        logger.debug(
            "  Rule %d: User %d, Site %d, %s %s %.1f%%, lead_time=%dh, last_triggered=%s",
            n.notification_id, n.user_id, n.site_id, n.metric, n.comparison,
            n.threshold, n.lead_time_hours, n.last_triggered_at
        )

    site_ids = {n.site_id for n in notifications}
    user_ids = {n.user_id for n in notifications}
    metrics = {n.metric for n in notifications}
    max_lead_hours = max((n.lead_time_hours for n in notifications), default=0)

    start_date = now.date()
    day_window = max(0, math.ceil(max_lead_hours / 24))
    end_date = start_date + timedelta(days=day_window)

    logger.info(
        "Querying predictions: sites=%s, metrics=%s, dates=%s to %s",
        sorted(site_ids), sorted(metrics), start_date, end_date
    )

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
        logger.info("No matching predictions found for date range and sites")
        return []

    logger.info("Found %d predictions matching criteria", len(predictions))
    for pred in predictions[:5]:  # Log first 5
        logger.debug(
            "  Prediction: Site %d, %s, %s=%.1f%%, computed_at=%s",
            pred.site_id, pred.date, pred.metric, pred.value * 100, pred.computed_at
        )

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

    total_subs = sum(len(subs) for subs in subscriptions_by_user.values())
    logger.info("Found %d active push subscriptions for %d users", total_subs, len(subscriptions_by_user))

    triggers: List[NotificationTrigger] = []

    for notification in notifications:
        key = (notification.site_id, notification.metric)
        preds = predictions_by_key.get(key, [])
        if not preds:
            logger.debug(
                "Rule %d: No predictions for site %d, metric %s",
                notification.notification_id, notification.site_id, notification.metric
            )
            continue
        window_end = now + timedelta(hours=notification.lead_time_hours)
        last_triggered = ensure_aware(notification.last_triggered_at)
        
        triggered_this_rule = False
        for pred in preds:
            if pred.date < start_date:
                logger.info(
                    "Rule %d: Prediction date %s is before start_date %s",
                    notification.notification_id, pred.date, start_date
                )
                continue
            if notification.lead_time_hours > 0 and pred.date > window_end.date():
                logger.info(
                    "Rule %d: Prediction date %s is beyond lead time window (ends %s)",
                    notification.notification_id, pred.date, window_end.date()
                )
                continue

            computed_at = ensure_aware(pred.computed_at)
            if last_triggered and computed_at and last_triggered >= computed_at:
                logger.info(
                    "Rule %d: Already triggered at %s for prediction computed at %s",
                    notification.notification_id, last_triggered, computed_at
                )
                continue

            comparator = COMPARISON_OPERATORS.get(notification.comparison)
            if not comparator:
                logger.warning(
                    "Rule %d: Unknown comparison operator '%s'",
                    notification.notification_id, notification.comparison
                )
                continue
            
            # Normalize threshold: predictions are stored as 0-1, but UI uses 0-100
            # So we need to convert threshold from percentage (0-100) to decimal (0-1)
            normalized_threshold = notification.threshold / 100.0
            
            if comparator(pred.value, normalized_threshold):
                logger.info(
                    "✓ Rule %d TRIGGERED: Site %d, %s=%.1f%% %s %.1f%% on %s",
                    notification.notification_id, notification.site_id,
                    notification.metric, pred.value * 100, notification.comparison,
                    notification.threshold, pred.date
                )
                payload = {
                    "notification_id": notification.notification_id,
                    "site_id": notification.site_id,
                    "site_name": site_names.get(notification.site_id),
                    "metric": notification.metric,
                    "comparison": notification.comparison,
                    "threshold": notification.threshold,
                    "value": pred.value * 100,  # Convert to percentage for display (0-100)
                    "prediction_date": pred.date.isoformat(),
                    "computed_at": computed_at.isoformat() if computed_at else None,
                    "gfs_forecast_at": ensure_aware(pred.gfs_forecast_at).isoformat()
                    if pred.gfs_forecast_at
                    else None,
                    "lead_time_hours": notification.lead_time_hours,
                    "triggered_at": now.isoformat(),
                }
                triggers.append(NotificationTrigger(notification=notification, prediction=pred, payload=payload))
                triggered_this_rule = True
                break
            else:
                logger.info(
                    "Rule %d: Threshold not met: %.1f%% %s %.1f%% = False",
                    notification.notification_id, pred.value * 100,
                    notification.comparison, notification.threshold
                )
        
        if not triggered_this_rule and preds:
            logger.debug("Rule %d: No predictions met the criteria", notification.notification_id)

    if not triggers:
        logger.info("No notification rules triggered")
        return []
    
    logger.info("Generated %d triggers", len(triggers))

    events: List[models.NotificationEvent] = []
    for trigger in triggers:
        notification = trigger.notification
        subscriptions = subscriptions_by_user.get(notification.user_id, [])
        if not subscriptions:
            logger.info(
                "Creating event for rule %d (no subscriptions, will be skipped)",
                notification.notification_id
            )
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
            logger.info(
                "Creating %d event(s) for rule %d (user %d has %d subscription(s))",
                len(subscriptions), notification.notification_id,
                notification.user_id, len(subscriptions)
            )
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

    logger.info("Created %d notification event(s), attempting delivery...", len(events))

    vapid_config: Optional[VapidConfig] = None
    try:
        vapid_config = get_vapid_configuration()
        logger.info("VAPID configuration loaded successfully")
    except PushConfigError as exc:
        logger.warning("Push delivery disabled: %s", exc)

    delivery_stats = {"sent": 0, "failed": 0, "skipped": 0, "config_missing": 0, "missing_subscription": 0}
    
    for event in events:
        if event.subscription_id is None:
            event.delivery_status = "skipped"
            delivery_stats["skipped"] += 1
            logger.debug("Event %d: No subscription, status=skipped", event.event_id)
            continue
        if not vapid_config:
            event.delivery_status = "config_missing"
            delivery_stats["config_missing"] += 1
            logger.debug("Event %d: No VAPID config, status=config_missing", event.event_id)
            continue
        try:
            if not event.subscription:
                # Relationship is not loaded; fetch fresh subscription
                event.subscription = await db.get(models.PushSubscription, event.subscription_id)
            if not event.subscription:
                event.delivery_status = "missing_subscription"
                delivery_stats["missing_subscription"] += 1
                logger.warning("Event %d: Subscription %d not found", event.event_id, event.subscription_id)
                continue
            await send_web_push(event.subscription, event.payload, vapid_config)
            event.delivery_status = "sent"
            delivery_stats["sent"] += 1
            logger.info(
                "Event %d: Push sent successfully to subscription %d",
                event.event_id, event.subscription_id
            )
        except PushDeliveryError as exc:
            logger.warning(
                "Failed to deliver push (event_id=%s, subscription_id=%s): %s",
                event.event_id, event.subscription_id, exc,
            )
            event.delivery_status = "failed"
            delivery_stats["failed"] += 1
        except Exception as exc:  # pragma: no cover - unexpected failures
            logger.error(
                "Unexpected push delivery error (event_id=%s, subscription_id=%s): %s",
                event.event_id, event.subscription_id, exc,
                exc_info=True,
            )
            event.delivery_status = "failed"
            delivery_stats["failed"] += 1

    await db.commit()
    for event in events:
        await db.refresh(event)
    
    logger.info(
        "Notification evaluation complete: %d events created, delivery status: %s",
        len(events), delivery_stats
    )
    return events
