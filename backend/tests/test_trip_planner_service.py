import calendar
import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app import crud
from app.services.trip_planner_service import (
    get_flight_stats_attr_for_metric,
    get_historical_prob,
    plan_trip_service,
)


def _site(site_id, name, latitude, longitude, altitude):
    return SimpleNamespace(
        site_id=site_id,
        name=name,
        latitude=latitude,
        longitude=longitude,
        altitude=altitude,
    )


def _prediction(site_id, forecast_date, value):
    return SimpleNamespace(site_id=site_id, date=forecast_date, value=value)


def _stats(site_id, year, month, metric, probability):
    days_in_month = calendar.monthrange(year, month)[1]
    return SimpleNamespace(
        site_id=site_id,
        month=month,
        **{get_flight_stats_attr_for_metric(metric): probability * days_in_month},
    )


def _stats_for_range(site_id, start_date, end_date, metric, probability):
    months = set()
    current = start_date
    while current <= end_date:
        months.add((current.year, current.month))
        current += datetime.timedelta(days=1)
    return [
        _stats(site_id, year, month, metric, probability)
        for year, month in sorted(months)
    ]


@pytest.mark.asyncio
async def test_plan_trip_prefers_forecasts_then_falls_back_and_ranks(monkeypatch):
    start_date = datetime.date.today()
    end_date = start_date + datetime.timedelta(days=1)
    metric = "XC20"
    sites = [
        _site(1, "Forecast Ridge", 50.0, 14.0, 900),
        _site(2, "Reliable Hill", 49.0, 15.0, 700),
        _site(3, "Quiet Slope", 48.0, 16.0, 500),
    ]
    predictions = [
        _prediction(1, start_date, 0.9),
        _prediction(2, start_date, 0.6),
    ]
    stats = [
        *_stats_for_range(1, start_date, end_date, metric, 0.3),
        *_stats_for_range(2, start_date, end_date, metric, 0.8),
        *_stats_for_range(3, start_date, end_date, metric, 0.2),
    ]

    get_predictions = AsyncMock(return_value=predictions)
    monkeypatch.setattr(crud, "get_predictions_for_range", get_predictions)
    monkeypatch.setattr(crud, "get_all_flight_stats", AsyncMock(return_value=stats))
    monkeypatch.setattr(crud, "get_sites", AsyncMock(return_value=sites))

    response = await plan_trip_service(
        db=object(),
        start_date=start_date,
        end_date=end_date,
        metric=metric,
        offset=0,
        limit=2,
    )

    assert response.total_count == 3
    assert response.has_more is True
    assert [site.site_name for site in response.sites] == ["Reliable Hill", "Forecast Ridge"]
    assert response.sites[0].average_flyability == 0.7
    assert response.sites[1].average_flyability == 0.6
    assert [day.source for day in response.sites[1].daily_probabilities] == [
        "forecast",
        "historical",
    ]
    assert [day.probability for day in response.sites[1].daily_probabilities] == [0.9, 0.3]
    get_predictions.assert_awaited_once_with(
        pytest.ANY,
        start_date=start_date,
        end_date=end_date,
        metric=metric,
    )


@pytest.mark.asyncio
async def test_plan_trip_applies_tags_altitude_and_distance_together(monkeypatch):
    plan_date = datetime.date.today()
    sites = [
        _site(1, "Matching Site", 0.0, 0.1, 1000),
        _site(2, "Too Far", 2.0, 2.0, 1000),
        _site(3, "Too Low", 0.0, 0.2, 300),
        _site(4, "Missing Tag", 0.0, 0.2, 1000),
    ]
    predictions = [_prediction(site.site_id, plan_date, 0.7) for site in sites]
    get_tags = AsyncMock(
        return_value={
            1: ["official", "alps", "school"],
            2: ["official", "alps"],
            3: ["official", "alps"],
            4: ["official"],
        }
    )

    monkeypatch.setattr(crud, "get_predictions_for_range", AsyncMock(return_value=predictions))
    monkeypatch.setattr(crud, "get_all_flight_stats", AsyncMock(return_value=[]))
    monkeypatch.setattr(crud, "get_sites", AsyncMock(return_value=sites))
    monkeypatch.setattr(crud, "get_tags_by_site_ids", get_tags)

    response = await plan_trip_service(
        db=object(),
        start_date=plan_date,
        end_date=plan_date,
        metric="XC0",
        user_latitude=0.0,
        user_longitude=0.0,
        max_distance_km=50,
        min_altitude_m=500,
        max_altitude_m=1500,
        required_tags=["official", "alps"],
    )

    assert response.total_count == 1
    assert response.has_more is False
    assert response.sites[0].site_name == "Matching Site"
    assert response.sites[0].distance_km == pytest.approx(11.1, abs=0.1)
    get_tags.assert_awaited_once_with(pytest.ANY, [1, 2, 3, 4])


@pytest.mark.asyncio
async def test_plan_trip_uses_historical_data_outside_forecast_horizon(monkeypatch):
    plan_date = datetime.date.today() + datetime.timedelta(days=8)
    site = _site(1, "Historical Site", 50.0, 14.0, 600)
    stats = _stats_for_range(1, plan_date, plan_date, "XC100", 0.25)
    get_predictions = AsyncMock(return_value=[])

    monkeypatch.setattr(crud, "get_predictions_for_range", get_predictions)
    monkeypatch.setattr(crud, "get_all_flight_stats", AsyncMock(return_value=stats))
    monkeypatch.setattr(crud, "get_sites", AsyncMock(return_value=[site]))

    response = await plan_trip_service(
        db=object(),
        start_date=plan_date,
        end_date=plan_date,
        metric="XC100",
    )

    assert response.sites[0].average_flyability == 0.25
    assert response.sites[0].daily_probabilities[0].source == "historical"
    assert response.sites[0].daily_probabilities[0].probability == 0.25
    get_predictions.assert_not_awaited()


@pytest.mark.asyncio
async def test_plan_trip_returns_empty_response_when_no_sites_exist(monkeypatch):
    plan_date = datetime.date.today()
    monkeypatch.setattr(crud, "get_predictions_for_range", AsyncMock(return_value=[]))
    monkeypatch.setattr(crud, "get_all_flight_stats", AsyncMock(return_value=[]))
    monkeypatch.setattr(crud, "get_sites", AsyncMock(return_value=[]))

    response = await plan_trip_service(
        db=object(),
        start_date=plan_date,
        end_date=plan_date,
    )

    assert response.sites == []
    assert response.total_count == 0
    assert response.has_more is False


def test_historical_probability_uses_selected_metric_and_month_length():
    stats = SimpleNamespace(month=2, avg_days_over_50=14.5)

    assert get_flight_stats_attr_for_metric("XC50") == "avg_days_over_50"
    assert get_flight_stats_attr_for_metric("unknown") == "avg_days_over_0"
    assert get_historical_prob(stats, 2024, 2, "XC50") == 0.5
