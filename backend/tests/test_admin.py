import os
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/glideator")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

from app.routers import admin
from app.security import effective_role, is_admin_identity


class FakeSession:
    def __init__(self, user):
        self.user = user

    async def get(self, model, user_id):
        return self.user if self.user.user_id == user_id else None


@pytest.mark.asyncio
async def test_require_admin_accepts_configured_email(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "owner@example.com")
    monkeypatch.setattr(admin, "decode_token", lambda token: {"sub": "7"})
    user = SimpleNamespace(
        user_id=7,
        email="owner@example.com",
        role="user",
        is_active=True,
    )

    result = await admin.require_admin("Bearer token", FakeSession(user))

    assert result is user
    assert effective_role(email=user.email, role=user.role) == "admin"


@pytest.mark.asyncio
async def test_require_admin_rejects_regular_user(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)
    monkeypatch.setattr(admin, "decode_token", lambda token: {"sub": "7"})
    user = SimpleNamespace(
        user_id=7,
        email="pilot@example.com",
        role="user",
        is_active=True,
    )

    with pytest.raises(HTTPException) as exc:
        await admin.require_admin("Bearer token", FakeSession(user))

    assert exc.value.status_code == 403


def test_database_admin_role_is_always_accepted(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAILS", raising=False)

    assert is_admin_identity(email="anyone@example.com", role="admin") is True


def test_admin_rates_are_safe_and_rounded():
    assert admin._rate(3, 4) == 75.0
    assert admin._rate(1, 3) == 33.3
    assert admin._rate(4, 0) == 0.0
    assert admin._coverage_percent(249, 250) == 99.6


def test_analytics_response_accepts_empty_period():
    response = admin.AdminAnalyticsResponse(
        window_days=30,
        total_events=0,
        unique_visitors=0,
        unique_sessions=0,
        map_sessions=0,
        site_detail_sessions=0,
        map_to_site_rate=0,
        daily=[],
        event_counts=[],
        top_paths=[],
        trip_planner=admin.AnalyticsFunnel(),
        recommendation_feedback=[],
        top_sites=[],
    )

    assert response.trip_planner.results_rate == 0
    assert response.recommendation_feedback == []


@pytest.mark.asyncio
async def test_forecast_check_queues_existing_celery_task(monkeypatch):
    calls = []

    class FakeTask:
        id = "task-123"

    def fake_send_task(name):
        calls.append(name)
        return FakeTask()

    monkeypatch.setattr(admin.celery, "send_task", fake_send_task)

    result = await admin.trigger_forecast_check(SimpleNamespace())

    assert result.task_id == "task-123"
    assert calls == ["app.celery_app.check_and_trigger_forecast_processing"]
