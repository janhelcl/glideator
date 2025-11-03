import os
import uuid
from datetime import datetime, timezone, date
from sqlalchemy import select

import pytest
from httpx import AsyncClient, ASGITransport

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/glideator")
os.environ.setdefault("CORS_ALLOW_ORIGINS", "http://localhost:3000")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("RATE_LIMIT_LOGIN_ATTEMPTS", "100")

from app.main import app
from app.database import AsyncSessionLocal
from app import models
from app.services.notifications import evaluate_and_queue_notifications


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
