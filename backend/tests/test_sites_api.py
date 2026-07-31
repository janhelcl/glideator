import os
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import ANY, AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/glideator")
os.environ.setdefault("CORS_ALLOW_ORIGINS", "http://localhost:3000")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")

from app import crud
from app.main import app


@pytest.mark.asyncio
async def test_predictions_endpoint_orders_metrics_and_fills_missing_values(monkeypatch):
    now = datetime(2026, 8, 1, 12, 0, 0)
    site = SimpleNamespace(
        site_id=42,
        name="Rana",
        latitude=50.404,
        longitude=13.771,
        altitude=457,
    )
    predictions = [
        SimpleNamespace(
            date=date(2026, 8, 2),
            metric="XC20",
            value=0.42,
            computed_at=now,
            gfs_forecast_at=now,
        ),
        SimpleNamespace(
            date=date(2026, 8, 2),
            metric="XC0",
            value=0.81,
            computed_at=now,
            gfs_forecast_at=now,
        ),
    ]

    monkeypatch.setattr(crud, "get_site", AsyncMock(return_value=site))
    monkeypatch.setattr(crud, "get_predictions", AsyncMock(return_value=predictions))
    monkeypatch.setattr(crud, "get_tags_by_site_id", AsyncMock(return_value=["flats", "official"]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/sites/42/predictions")

    assert response.status_code == 200
    payload = response.json()[0]
    assert payload["site_id"] == 42
    assert payload["tags"] == ["flats", "official"]
    assert payload["predictions"][0]["date"] == "2026-08-02"
    assert payload["predictions"][0]["values"] == [
        0.81,
        0.0,
        0.42,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    ]


@pytest.mark.asyncio
async def test_predictions_endpoint_returns_404_for_unknown_site(monkeypatch):
    monkeypatch.setattr(crud, "get_site", AsyncMock(return_value=None))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/sites/999/predictions")

    assert response.status_code == 404
    assert response.json() == {"detail": "Site not found"}


@pytest.mark.asyncio
async def test_forecast_endpoint_serializes_forecast_payloads(monkeypatch):
    now = datetime(2026, 8, 1, 6, 0, 0)
    site = SimpleNamespace(site_id=7, lat_gfs=50.0, lon_gfs=14.0)
    forecast = SimpleNamespace(
        date=date(2026, 8, 3),
        computed_at=now,
        gfs_forecast_at=now,
        lat_gfs=50.0,
        lon_gfs=14.0,
        forecast_9={"wind_speed": 3.2},
        forecast_12={"wind_speed": 4.1},
        forecast_15={"wind_speed": 5.0},
    )

    monkeypatch.setattr(crud, "get_site", AsyncMock(return_value=site))
    get_forecast = AsyncMock(return_value=forecast)
    monkeypatch.setattr(crud, "get_forecast", get_forecast)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/sites/7/forecast", params={"query_date": "2026-08-03"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["forecast_9"] == {"wind_speed": 3.2}
    assert payload["forecast_12"] == {"wind_speed": 4.1}
    assert payload["forecast_15"] == {"wind_speed": 5.0}
    get_forecast.assert_awaited_once_with(
        ANY,
        date(2026, 8, 3),
        50.0,
        14.0,
    )


@pytest.mark.asyncio
async def test_spots_endpoint_distinguishes_empty_result_from_missing_site(monkeypatch):
    monkeypatch.setattr(crud, "get_site", AsyncMock(return_value=SimpleNamespace(site_id=11)))
    monkeypatch.setattr(crud, "get_spots_by_site_id", AsyncMock(return_value=[]))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/sites/11/spots")

    assert response.status_code == 200
    assert response.json() == []

    monkeypatch.setattr(crud, "get_site", AsyncMock(return_value=None))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        missing_response = await client.get("/sites/11/spots")

    assert missing_response.status_code == 404
    assert missing_response.json() == {"detail": "Site with ID 11 not found"}
