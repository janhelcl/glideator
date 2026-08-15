import os
from unittest.mock import ANY, AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/glideator")
os.environ.setdefault("CORS_ALLOW_ORIGINS", "http://localhost:3000")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

from app.main import app
from app.services import trip_planner_service


@pytest.mark.asyncio
async def test_plan_trip_rejects_reversed_date_range(monkeypatch):
    plan_service = AsyncMock()
    monkeypatch.setattr(trip_planner_service, "plan_trip_service", plan_service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/plan-trip",
            json={
                "start_date": "2026-08-10",
                "end_date": "2026-08-01",
                "metric": "XC0",
            },
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Start date cannot be after end date."}
    plan_service.assert_not_awaited()


@pytest.mark.asyncio
async def test_plan_trip_forwards_filters_and_pagination(monkeypatch):
    service_response = {
        "sites": [
            {
                "site_name": "Rana",
                "average_flyability": 0.76,
                "site_id": 1,
                "latitude": 50.404,
                "longitude": 13.771,
                "altitude": 457,
                "distance_km": 63.4,
                "daily_probabilities": [
                    {
                        "date": "2026-08-02",
                        "probability": 0.76,
                        "source": "forecast",
                    }
                ],
            }
        ],
        "total_count": 21,
        "has_more": True,
    }
    plan_service = AsyncMock(return_value=service_response)
    monkeypatch.setattr(trip_planner_service, "plan_trip_service", plan_service)

    request_payload = {
        "start_date": "2026-08-02",
        "end_date": "2026-08-04",
        "metric": "XC20",
        "user_latitude": 50.0755,
        "user_longitude": 14.4378,
        "max_distance_km": 250,
        "min_altitude_m": 100,
        "max_altitude_m": 1800,
        "required_tags": ["official", "alps"],
        "offset": 10,
        "limit": 5,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/plan-trip", json=request_payload)

    assert response.status_code == 200
    assert response.json() == service_response
    plan_service.assert_awaited_once_with(
        db=ANY,
        start_date=ANY,
        end_date=ANY,
        metric="XC20",
        user_latitude=50.0755,
        user_longitude=14.4378,
        max_distance_km=250.0,
        min_altitude_m=100,
        max_altitude_m=1800,
        required_tags=["official", "alps"],
        offset=10,
        limit=5,
    )
    call_kwargs = plan_service.await_args.kwargs
    assert call_kwargs["start_date"].isoformat() == "2026-08-02"
    assert call_kwargs["end_date"].isoformat() == "2026-08-04"


@pytest.mark.asyncio
async def test_plan_trip_rejects_unknown_metric_before_service_call(monkeypatch):
    plan_service = AsyncMock()
    monkeypatch.setattr(trip_planner_service, "plan_trip_service", plan_service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/plan-trip",
            json={
                "start_date": "2026-08-01",
                "end_date": "2026-08-02",
                "metric": "XC15",
            },
        )

    assert response.status_code == 422
    plan_service.assert_not_awaited()
