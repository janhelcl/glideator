import os

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/glideator")
os.environ.setdefault("CORS_ALLOW_ORIGINS", "http://localhost:3000")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

from app.main import app
from app.routers import analytics


class FakeSession:
    def __init__(self):
        self.added = None
        self.committed = False

    def add(self, row):
        self.added = row

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_product_event_is_accepted_without_personal_data(monkeypatch):
    session = FakeSession()

    async def override_get_db():
        yield session

    monkeypatch.setattr(analytics, "_apply_analytics_rate_limit", lambda **kwargs: None)
    app.dependency_overrides[analytics.get_db] = override_get_db

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/analytics/events",
                json={
                    "event_name": "trip_plan_submitted",
                    "anonymous_id": "anonymous-12345",
                    "session_id": "session-12345",
                    "path": "/trip-planner",
                    "properties": {
                        "metric": "XC20",
                        "distance_enabled": True,
                        "tags_count": 2,
                    },
                },
            )
    finally:
        app.dependency_overrides.pop(analytics.get_db, None)

    assert response.status_code == 202
    assert response.json() == {"accepted": True}
    assert session.committed is True
    assert session.added.event_name == "trip_plan_submitted"
    assert session.added.anonymous_id == "anonymous-12345"
    assert session.added.session_id == "session-12345"
    assert session.added.path == "/trip-planner"
    assert session.added.properties == {
        "metric": "XC20",
        "distance_enabled": True,
        "tags_count": 2,
    }
    assert not hasattr(session.added, "ip_address")
    assert not hasattr(session.added, "user_agent")


@pytest.mark.asyncio
async def test_product_event_rejects_invalid_event_names(monkeypatch):
    monkeypatch.setattr(analytics, "_apply_analytics_rate_limit", lambda **kwargs: None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/analytics/events",
            json={
                "event_name": "Trip Plan Submitted",
                "anonymous_id": "anonymous-12345",
                "session_id": "session-12345",
                "properties": {},
            },
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_product_event_limits_property_payload(monkeypatch):
    monkeypatch.setattr(analytics, "_apply_analytics_rate_limit", lambda **kwargs: None)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/analytics/events",
            json={
                "event_name": "page_view",
                "anonymous_id": "anonymous-12345",
                "session_id": "session-12345",
                "properties": {"large": "x" * 12_100},
            },
        )

    assert response.status_code == 422
