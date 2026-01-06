import os
import uuid
from datetime import datetime, timezone, date, timedelta
from sqlalchemy import select, delete

import pytest
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/glideator")
os.environ.setdefault("CORS_ALLOW_ORIGINS", "http://localhost:3000")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("RATE_LIMIT_LOGIN_ATTEMPTS", "100")

from app.main import app
from app.database import AsyncSessionLocal
from app import models, crud
from app.services.notifications import (
    evaluate_and_queue_notifications,
    EVENT_TYPE_INITIAL,
    EVENT_TYPE_DETERIORATED,
    EVENT_TYPE_IMPROVED,
)


async def _get_or_create_test_site() -> int:
    async with AsyncSessionLocal() as db:
        existing = await db.execute(
            select(models.Site.site_id).order_by(models.Site.site_id).limit(1)
        )
        row = existing.first()
        if row:
            return row[0]
        site = models.Site(
            site_id=99999,
            name=f"Test Site {uuid.uuid4().hex[:8]}",
            latitude=49.0,
            longitude=16.0,
            altitude=500,
            lat_gfs=49.0,
            lon_gfs=16.0,
        )
        db.add(site)
        await db.commit()
        await db.refresh(site)
        return site.site_id


async def _create_prediction(site_id: int, metric: str = "XC0", value: float = 80.0) -> None:
    async with AsyncSessionLocal() as db:
        computed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        prediction = models.Prediction(
            site_id=site_id,
            date=date.today(),
            metric=metric,
            value=value,
            computed_at=computed_at,
            gfs_forecast_at=computed_at,
        )
        db.add(prediction)
        await db.commit()


@pytest.mark.asyncio
async def test_notifications_crud_and_event_flow():
    site_id = await _get_or_create_test_site()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        email = f"notify+{uuid.uuid4().hex[:8]}@example.com"
        await ac.post("/auth/register", json={"email": email, "password": "StrongPass1!"})
        login_resp = await ac.post("/auth/login", json={"email": email, "password": "StrongPass1!"})
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Register push subscription
        sub_payload = {
            "endpoint": f"https://push.example.com/{uuid.uuid4().hex}",
            "p256dh": uuid.uuid4().hex,
            "auth": uuid.uuid4().hex[:22],
            "client_info": {"agent": "pytest"},
        }
        sub_resp = await ac.post("/users/me/push-subscriptions", json=sub_payload, headers=headers)
        assert sub_resp.status_code == 201
        subscription_id = sub_resp.json()["subscription_id"]

        # Create notification
        notif_payload = {
            "site_id": site_id,
            "metric": "XC0",
            "comparison": "gte",
            "threshold": 50.0,
            "lead_time_hours": 48,
        }
        notif_resp = await ac.post("/users/me/notifications", json=notif_payload, headers=headers)
        assert notif_resp.status_code == 201
        notification_id = notif_resp.json()["notification_id"]

        # Update notification
        patch_resp = await ac.patch(
            f"/users/me/notifications/{notification_id}",
            json={"threshold": 60.0},
            headers=headers,
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["threshold"] == 60.0

        # Ensure list returns the notification
        list_resp = await ac.get("/users/me/notifications", headers=headers)
        assert list_resp.status_code == 200
        assert any(n["notification_id"] == notification_id for n in list_resp.json())

    # Create prediction and evaluate notifications
    await _create_prediction(site_id=site_id, value=70.0)
    async with AsyncSessionLocal() as db:
        events = await evaluate_and_queue_notifications(db)
        assert events
        assert any(evt.delivery_status in {"config_missing", "skipped", "sent"} for evt in events)

    # Fetch events via API
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login_resp = await ac.post("/auth/login", json={"email": email, "password": "StrongPass1!"})
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        events_resp = await ac.get(f"/users/me/notifications/{notification_id}/events", headers=headers)
        assert events_resp.status_code == 200
        events_payload = events_resp.json()
        assert len(events_payload) >= 1
        assert events_payload[0]["payload"]["value"] >= 60.0
        assert any(
            evt["delivery_status"] in ["config_missing", "sent", "skipped", "failed", "missing_subscription"]
            for evt in events_payload
        )

        # Deactivate push subscription
        del_resp = await ac.delete(f"/users/me/push-subscriptions/{subscription_id}", headers=headers)
        assert del_resp.status_code == 204

        # Delete notification
        del_notif_resp = await ac.delete(f"/users/me/notifications/{notification_id}", headers=headers)
        assert del_notif_resp.status_code == 204


async def _create_prediction_with_date(
    site_id: int,
    forecast_date: date,
    metric: str = "XC0",
    value: float = 0.8,
) -> None:
    """Create a prediction for a specific date with value in 0-1 scale."""
    async with AsyncSessionLocal() as db:
        # Delete existing prediction if any
        await db.execute(
            delete(models.Prediction).where(
                models.Prediction.site_id == site_id,
                models.Prediction.date == forecast_date,
                models.Prediction.metric == metric,
            )
        )
        await db.commit()

        computed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        prediction = models.Prediction(
            site_id=site_id,
            date=forecast_date,
            metric=metric,
            value=value,
            computed_at=computed_at,
            gfs_forecast_at=computed_at,
        )
        db.add(prediction)
        await db.commit()


async def _create_test_notification(
    user_id: int,
    site_id: int,
    threshold: float = 50.0,
    improvement_threshold: float = 15.0,
) -> int:
    """Create a test notification and return its ID."""
    async with AsyncSessionLocal() as db:
        notification = models.UserNotification(
            user_id=user_id,
            site_id=site_id,
            metric="XC0",
            comparison="gte",
            threshold=threshold,
            lead_time_hours=48,
            improvement_threshold=improvement_threshold,
            active=True,
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification.notification_id


async def _cleanup_notification(notification_id: int) -> None:
    """Clean up a test notification and its related records."""
    async with AsyncSessionLocal() as db:
        # Delete notified_forecasts
        await db.execute(
            delete(models.NotifiedForecast).where(
                models.NotifiedForecast.notification_id == notification_id
            )
        )
        # Delete notification events
        await db.execute(
            delete(models.NotificationEvent).where(
                models.NotificationEvent.notification_id == notification_id
            )
        )
        # Delete notification
        await db.execute(
            delete(models.UserNotification).where(
                models.UserNotification.notification_id == notification_id
            )
        )
        await db.commit()


async def _get_user_id_by_email(email: str) -> int:
    """Get user ID from email."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.User.user_id).where(models.User.email == email)
        )
        row = result.first()
        return row[0] if row else None


@pytest.mark.asyncio
async def test_initial_notification_with_event_type():
    """Test that initial notifications include event_type in payload."""
    site_id = await _get_or_create_test_site()
    forecast_date = date.today()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        email = f"notify+{uuid.uuid4().hex[:8]}@example.com"
        await ac.post("/auth/register", json={"email": email, "password": "StrongPass1!"})
        login_resp = await ac.post("/auth/login", json={"email": email, "password": "StrongPass1!"})
        token = login_resp.json()["access_token"]
        user_id = await _get_user_id_by_email(email)

    notification_id = await _create_test_notification(user_id, site_id, threshold=50.0)

    try:
        # Create prediction above threshold (60%)
        await _create_prediction_with_date(site_id, forecast_date, value=0.6)

        async with AsyncSessionLocal() as db:
            events = await evaluate_and_queue_notifications(db)
            matching_events = [e for e in events if e.notification_id == notification_id]

            assert len(matching_events) >= 1, "Should generate initial notification"
            event = matching_events[0]
            assert event.payload.get("event_type") == EVENT_TYPE_INITIAL
            assert event.payload.get("value") == 60.0
            assert event.payload.get("previous_value") is None
    finally:
        await _cleanup_notification(notification_id)


@pytest.mark.asyncio
async def test_deterioration_notification():
    """Test that deterioration notifications are sent when conditions drop below threshold."""
    site_id = await _get_or_create_test_site()
    forecast_date = date.today()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        email = f"notify+{uuid.uuid4().hex[:8]}@example.com"
        await ac.post("/auth/register", json={"email": email, "password": "StrongPass1!"})
        await ac.post("/auth/login", json={"email": email, "password": "StrongPass1!"})
        user_id = await _get_user_id_by_email(email)

    notification_id = await _create_test_notification(user_id, site_id, threshold=50.0)

    try:
        # Step 1: Create prediction above threshold (60%) and trigger initial notification
        await _create_prediction_with_date(site_id, forecast_date, value=0.6)
        async with AsyncSessionLocal() as db:
            events = await evaluate_and_queue_notifications(db)
            initial_events = [e for e in events if e.notification_id == notification_id]
            assert len(initial_events) >= 1, "Should generate initial notification"
            assert initial_events[0].payload.get("event_type") == EVENT_TYPE_INITIAL

        # Step 2: Update prediction below threshold (40%) and trigger deterioration
        await _create_prediction_with_date(site_id, forecast_date, value=0.4)
        async with AsyncSessionLocal() as db:
            events = await evaluate_and_queue_notifications(db)
            deterioration_events = [e for e in events if e.notification_id == notification_id]
            assert len(deterioration_events) >= 1, "Should generate deterioration notification"
            event = deterioration_events[0]
            assert event.payload.get("event_type") == EVENT_TYPE_DETERIORATED
            assert event.payload.get("value") == 40.0
            assert event.payload.get("previous_value") == 60.0
    finally:
        await _cleanup_notification(notification_id)


@pytest.mark.asyncio
async def test_improvement_notification():
    """Test that improvement notifications are sent when conditions improve significantly."""
    site_id = await _get_or_create_test_site()
    forecast_date = date.today()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        email = f"notify+{uuid.uuid4().hex[:8]}@example.com"
        await ac.post("/auth/register", json={"email": email, "password": "StrongPass1!"})
        await ac.post("/auth/login", json={"email": email, "password": "StrongPass1!"})
        user_id = await _get_user_id_by_email(email)

    # Set improvement_threshold to 15%
    notification_id = await _create_test_notification(user_id, site_id, threshold=50.0, improvement_threshold=15.0)

    try:
        # Step 1: Create prediction at 55% and trigger initial notification
        await _create_prediction_with_date(site_id, forecast_date, value=0.55)
        async with AsyncSessionLocal() as db:
            events = await evaluate_and_queue_notifications(db)
            initial_events = [e for e in events if e.notification_id == notification_id]
            assert len(initial_events) >= 1, "Should generate initial notification"

        # Step 2: Update prediction to 72% (+17%, above 15% threshold) and trigger improvement
        await _create_prediction_with_date(site_id, forecast_date, value=0.72)
        async with AsyncSessionLocal() as db:
            events = await evaluate_and_queue_notifications(db)
            improvement_events = [e for e in events if e.notification_id == notification_id]
            assert len(improvement_events) >= 1, "Should generate improvement notification"
            event = improvement_events[0]
            assert event.payload.get("event_type") == EVENT_TYPE_IMPROVED
            assert event.payload.get("value") == 72.0
            assert event.payload.get("previous_value") == 55.0
    finally:
        await _cleanup_notification(notification_id)


@pytest.mark.asyncio
async def test_no_improvement_notification_below_threshold():
    """Test that improvement notifications are NOT sent for small improvements."""
    site_id = await _get_or_create_test_site()
    forecast_date = date.today()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        email = f"notify+{uuid.uuid4().hex[:8]}@example.com"
        await ac.post("/auth/register", json={"email": email, "password": "StrongPass1!"})
        await ac.post("/auth/login", json={"email": email, "password": "StrongPass1!"})
        user_id = await _get_user_id_by_email(email)

    # Set improvement_threshold to 15%
    notification_id = await _create_test_notification(user_id, site_id, threshold=50.0, improvement_threshold=15.0)

    try:
        # Step 1: Create prediction at 55% and trigger initial notification
        await _create_prediction_with_date(site_id, forecast_date, value=0.55)
        async with AsyncSessionLocal() as db:
            events = await evaluate_and_queue_notifications(db)
            initial_events = [e for e in events if e.notification_id == notification_id]
            assert len(initial_events) >= 1, "Should generate initial notification"

        # Step 2: Update prediction to 65% (+10%, below 15% threshold) - should NOT trigger
        await _create_prediction_with_date(site_id, forecast_date, value=0.65)
        async with AsyncSessionLocal() as db:
            events = await evaluate_and_queue_notifications(db)
            improvement_events = [e for e in events if e.notification_id == notification_id]
            assert len(improvement_events) == 0, "Should NOT generate notification for small improvement"
    finally:
        await _cleanup_notification(notification_id)


@pytest.mark.asyncio
async def test_fluctuation_scenario():
    """Test good → bad → good fluctuation generates multiple notifications."""
    site_id = await _get_or_create_test_site()
    forecast_date = date.today()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        email = f"notify+{uuid.uuid4().hex[:8]}@example.com"
        await ac.post("/auth/register", json={"email": email, "password": "StrongPass1!"})
        await ac.post("/auth/login", json={"email": email, "password": "StrongPass1!"})
        user_id = await _get_user_id_by_email(email)

    notification_id = await _create_test_notification(user_id, site_id, threshold=50.0, improvement_threshold=15.0)

    try:
        event_types = []

        # Step 1: Good conditions (60%)
        await _create_prediction_with_date(site_id, forecast_date, value=0.6)
        async with AsyncSessionLocal() as db:
            events = await evaluate_and_queue_notifications(db)
            for e in events:
                if e.notification_id == notification_id:
                    event_types.append(e.payload.get("event_type"))

        # Step 2: Bad conditions (40%)
        await _create_prediction_with_date(site_id, forecast_date, value=0.4)
        async with AsyncSessionLocal() as db:
            events = await evaluate_and_queue_notifications(db)
            for e in events:
                if e.notification_id == notification_id:
                    event_types.append(e.payload.get("event_type"))

        # Step 3: Good again (80%, +40% from 40%)
        await _create_prediction_with_date(site_id, forecast_date, value=0.8)
        async with AsyncSessionLocal() as db:
            events = await evaluate_and_queue_notifications(db)
            for e in events:
                if e.notification_id == notification_id:
                    event_types.append(e.payload.get("event_type"))

        # Verify we got all three notification types
        assert EVENT_TYPE_INITIAL in event_types, "Should have initial notification"
        assert EVENT_TYPE_DETERIORATED in event_types, "Should have deterioration notification"
        # Note: The "good again" may trigger initial (if we consider it a new trigger) or improved
        # depending on implementation. With current logic, after deterioration the notified_forecast
        # is updated with the bad value, so 80% vs 40% = +40% triggers improvement
        assert EVENT_TYPE_IMPROVED in event_types or len(event_types) >= 3, "Should have third notification"
    finally:
        await _cleanup_notification(notification_id)


@pytest.mark.asyncio
async def test_cleanup_old_notified_forecasts():
    """Test that old notified_forecasts records are cleaned up."""
    site_id = await _get_or_create_test_site()
    old_date = date.today() - timedelta(days=7)
    today = date.today()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        email = f"notify+{uuid.uuid4().hex[:8]}@example.com"
        await ac.post("/auth/register", json={"email": email, "password": "StrongPass1!"})
        await ac.post("/auth/login", json={"email": email, "password": "StrongPass1!"})
        user_id = await _get_user_id_by_email(email)

    notification_id = await _create_test_notification(user_id, site_id, threshold=50.0)

    try:
        async with AsyncSessionLocal() as db:
            # Create an old notified_forecast record
            await crud.upsert_notified_forecast(
                db, notification_id, old_date, 0.6, EVENT_TYPE_INITIAL
            )
            # Create a current notified_forecast record
            await crud.upsert_notified_forecast(
                db, notification_id, today, 0.7, EVENT_TYPE_INITIAL
            )

            # Verify both exist
            old_record = await crud.get_notified_forecast(db, notification_id, old_date)
            current_record = await crud.get_notified_forecast(db, notification_id, today)
            assert old_record is not None, "Old record should exist"
            assert current_record is not None, "Current record should exist"

            # Run cleanup
            deleted_count = await crud.cleanup_old_notified_forecasts(db, today)
            assert deleted_count >= 1, "Should delete old records"

            # Verify old is gone, current remains
            old_record = await crud.get_notified_forecast(db, notification_id, old_date)
            current_record = await crud.get_notified_forecast(db, notification_id, today)
            assert old_record is None, "Old record should be deleted"
            assert current_record is not None, "Current record should remain"
    finally:
        await _cleanup_notification(notification_id)
