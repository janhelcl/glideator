import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/glideator")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

from app.routers import admin, admin_analytics


class FakeMappings:
    def __init__(self, row):
        self.row = row

    def one(self):
        return self.row


class FakeResult:
    def __init__(self, row):
        self.row = row

    def mappings(self):
        return FakeMappings(self.row)


class FakeDb:
    def __init__(self, row):
        self.row = row
        self.statement = None

    async def execute(self, statement, params):
        self.statement = str(statement)
        return FakeResult(self.row)


def empty_base_response():
    return admin.AdminAnalyticsResponse(
        window_days=30,
        total_events=20,
        unique_visitors=8,
        unique_sessions=10,
        map_sessions=9,
        site_detail_sessions=7,
        map_to_site_rate=77.8,
        daily=[],
        event_counts=[],
        top_paths=[],
        trip_planner=admin.AnalyticsFunnel(
            submitted_sessions=0,
            results_sessions=4,
            opened_site_sessions=2,
            results_rate=0,
            site_open_rate=50,
        ),
        recommendation_feedback=[],
        top_sites=[],
    )


def test_ratio_is_safe_and_rounded():
    assert admin_analytics._ratio(7, 4) == 1.75
    assert admin_analytics._ratio(1, 3) == 0.33
    assert admin_analytics._ratio(4, 0) == 0.0


@pytest.mark.asyncio
async def test_engagement_metrics_use_sequenced_session_denominators(monkeypatch):
    base = empty_base_response()

    async def fake_legacy_analytics(*, days, _, db):
        assert days == 30
        return base

    monkeypatch.setattr(admin_analytics.admin, "get_analytics", fake_legacy_analytics)
    db = FakeDb(
        {
            "map_sessions": 4,
            "map_to_site_sessions": 3,
            "map_site_open_events": 7,
            "planner_sessions": 5,
            "submitted_sessions": 2,
            "results_sessions": 4,
            "opened_site_sessions": 2,
        }
    )

    result = await admin_analytics.get_analytics(days=30, _=SimpleNamespace(), db=db)

    assert result.map_sessions == 4
    assert result.site_detail_sessions == 7
    assert result.map_to_site_sessions == 3
    assert result.map_to_site_rate == 75.0
    assert result.map_site_open_events == 7
    assert result.sites_opened_per_map_session == 1.75
    assert result.trip_planner.planner_sessions == 5
    assert result.trip_planner.submitted_sessions == 2
    assert result.trip_planner.results_sessions == 4
    assert result.trip_planner.results_rate == 80.0
    assert result.trip_planner.opened_site_sessions == 2
    assert result.trip_planner.site_open_rate == 50.0
    assert "e.created_at >= m.first_map_at" in db.statement
    assert "e.created_at >= p.first_planner_at" in db.statement
