import os
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/glideator")

from app import crud, mcp_analytics, schemas
from app.mcp import (
    FORECAST_CHART_URI,
    FORECAST_CHART_V1_URI,
    FORECAST_MAP_URI,
    SEASONALITY_CHART_URI,
    _normalize_site_name,
    _serialize_site_info,
    get_site_seasonal_stats,
    mcp,
)


EXPECTED_TOOLS = {
    "find_sites",
    "list_sites",
    "get_site_info",
    "get_site_resources",
    "get_site_seasonal_stats",
    "show_site_seasonality_chart",
    "get_site_predictions",
    "show_site_forecast_chart",
    "show_forecast_map",
    "get_site_takeoffs_and_landings",
    "plan_trip",
}


def test_mcp_uses_stateless_json_http_transport():
    assert mcp.settings.stateless_http is True
    assert mcp.settings.json_response is True


def test_site_search_normalization_is_accent_insensitive():
    assert _normalize_site_name("Rana") == _normalize_site_name("Raná")
    assert _normalize_site_name("  KÖSSEN ") == _normalize_site_name("Kossen")


def test_site_info_orm_is_converted_to_public_schema():
    orm_record = SimpleNamespace(
        site_id=1,
        site_name="Raná",
        country="Czechia",
        html="<p>Site guide</p>",
    )

    result = _serialize_site_info(orm_record)

    assert isinstance(result, schemas.SiteInfo)
    assert result.model_dump() == {
        "site_id": 1,
        "site_name": "Raná",
        "country": "Czechia",
        "html": "<p>Site guide</p>",
    }


def test_trip_plan_site_ids_are_integers():
    site_id_schema = schemas.SiteSuggestion.model_json_schema()["properties"]["site_id"]
    assert site_id_schema["type"] == "integer"


@pytest.mark.asyncio
async def test_all_mcp_tools_declare_public_review_annotations():
    tools = await mcp.list_tools()
    tools_by_name = {tool.name: tool for tool in tools}

    assert EXPECTED_TOOLS.issubset(tools_by_name)

    for name in EXPECTED_TOOLS:
        tool = tools_by_name[name]
        assert tool.title
        assert tool.description
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.openWorldHint is False


@pytest.mark.asyncio
async def test_find_sites_public_schema_stays_stable():
    """Guard the plugin-review contract while search internals evolve."""
    tools = await mcp.list_tools()
    find_sites = next(tool for tool in tools if tool.name == "find_sites")

    properties = find_sites.inputSchema["properties"]
    assert set(properties) == {"query", "limit"}
    assert properties["query"]["type"] == "string"
    assert properties["limit"]["type"] == "integer"
    assert properties["limit"]["default"] == 10
    assert find_sites.inputSchema["required"] == ["query"]

    site_item_schema = schemas.SiteListItem.model_json_schema()
    assert site_item_schema["required"] == ["site_id", "name"]
    assert site_item_schema["properties"]["site_id"]["type"] == "integer"
    assert site_item_schema["properties"]["name"]["type"] == "string"


@pytest.mark.asyncio
async def test_site_resources_exposes_structured_public_output():
    tools = await mcp.list_tools()
    resources = next(tool for tool in tools if tool.name == "get_site_resources")

    assert resources.outputSchema is not None
    properties = resources.outputSchema["properties"]
    assert properties["site_id"]["type"] == "integer"
    assert "local_resources" in properties
    assert "webcam_urls" in properties
    assert "meteostation_urls" in properties
    assert "source_run_id" not in properties
    assert "run_extracted_at" not in properties


@pytest.mark.asyncio
async def test_forecast_chart_advertises_readable_mcp_app_resource():
    tools = {tool.name: tool for tool in await mcp.list_tools()}
    assert tools["show_site_forecast_chart"].meta["ui"]["resourceUri"] == FORECAST_CHART_URI
    assert tools["get_site_predictions"].meta is None

    resource, = await mcp.read_resource(FORECAST_CHART_URI)
    assert resource.mime_type == "text/html;profile=mcp-app"
    assert resource.meta["ui"]["csp"] == {}
    assert "ui/notifications/tool-result" in resource.content
    assert 'id="flight-quality"' in resource.content
    assert 'id="flight-forecast"' in resource.content
    legacy_resource, = await mcp.read_resource(FORECAST_CHART_V1_URI)
    assert legacy_resource.mime_type == "text/html;profile=mcp-app"


@pytest.mark.asyncio
async def test_forecast_chart_returns_sorted_probabilities_and_text(monkeypatch):
    first, second = date(2030, 1, 1), date(2030, 1, 2)
    monkeypatch.setattr(crud, "get_site", AsyncMock(return_value=SimpleNamespace(name="Raná")))
    monkeypatch.setattr(crud, "get_predictions", AsyncMock(return_value=[
        SimpleNamespace(date=second, metric="XC0", value=0.4),
        SimpleNamespace(date=first, metric="XC50", value=0.0),
        SimpleNamespace(date=first, metric="XC0", value=0.67),
    ]))
    monkeypatch.setattr(mcp_analytics, "_record_mcp_tool_event", AsyncMock())

    result = await mcp.call_tool(
        "show_site_forecast_chart", {"site_id": 42, "metric": "XC50", "query_date": "2030-01-03"}
    )

    assert result.structuredContent == {
        "site_id": 42,
        "site_name": "Raná",
        "metric": "XC50",
        "selected_date": "2030-01-03",
        "days": [
            {"date": "2030-01-01", "probabilities": {"XC0": 0.67, "XC50": 0.0}},
            {"date": "2030-01-02", "probabilities": {"XC0": 0.4}},
        ],
    }
    assert "2030-01-01  0%" in result.content[0].text
    assert "2030-01-02  No data" in result.content[0].text
    assert "No forecast is available for 2030-01-03" in result.content[0].text


@pytest.mark.asyncio
async def test_seasonality_chart_preserves_months_and_raw_statistics(monkeypatch):
    months = [
        SimpleNamespace(month=month, **{
            f"avg_days_over_{threshold}": value if threshold == 50 else 0.0
            for threshold in range(0, 101, 10)
        })
        for month, value in [(1, 0.0), (3, 5.2)]
    ]
    monkeypatch.setattr(crud, "get_site", AsyncMock(return_value=SimpleNamespace(name="Bassano")))
    monkeypatch.setattr(crud, "get_flight_stats_by_site_id", AsyncMock(return_value=months))
    monkeypatch.setattr(mcp_analytics, "_record_mcp_tool_event", AsyncMock())

    tools = {tool.name: tool for tool in await mcp.list_tools()}
    assert tools["show_site_seasonality_chart"].meta["ui"]["resourceUri"] == SEASONALITY_CHART_URI
    assert tools["get_site_seasonal_stats"].meta is None
    resource, = await mcp.read_resource(SEASONALITY_CHART_URI)
    assert resource.mime_type == "text/html;profile=mcp-app"
    assert resource.meta["ui"]["csp"] == {}
    assert 'id="seasonality"' in resource.content

    raw = await get_site_seasonal_stats(133)
    result = await mcp.call_tool("show_site_seasonality_chart", {"site_id": 133, "metric": "XC50"})
    data = result.structuredContent
    assert data["site_name"] == "Bassano"
    assert data["metric"] == "XC50"
    assert [row["month"] for row in data["months"]] == [1, 3]
    assert data["months"][0]["average_days"]["XC50"] == raw["January"]["days_over_50XC_points_or_more"] == 0.0
    assert data["months"][1]["average_days"]["XC50"] == raw["March"]["days_over_50XC_points_or_more"] == 5.2
    assert len(data["months"][1]["average_days"]) == 11
    assert "March  5.2 days" in result.content[0].text
    assert "February" not in result.content[0].text


@pytest.mark.asyncio
async def test_forecast_map_sends_forecasts_to_widget_and_selection_to_model(monkeypatch):
    sites = [
        schemas.SiteResponse(
            name="Bassano", latitude=45.8, longitude=11.7, altitude=800, site_id=133, tags=["Alps"],
            predictions=[schemas.PredictionValues(
                date="2030-01-02", values=[0.75] * 11,
                computed_at="2030-01-01T00:00:00", gfs_forecast_at="2030-01-01T00:00:00",
            )],
        ),
        schemas.SiteResponse(
            name="Raná", latitude=50.4, longitude=13.8, altitude=457, site_id=1,
            predictions=[], tags=[],
        ),
    ]
    monkeypatch.setattr(crud, "get_sites_with_predictions", AsyncMock(return_value=sites))
    monkeypatch.setattr(mcp_analytics, "_record_mcp_tool_event", AsyncMock())

    tools = {tool.name: tool for tool in await mcp.list_tools()}
    assert tools["show_forecast_map"].meta["ui"]["resourceUri"] == FORECAST_MAP_URI
    resource, = await mcp.read_resource(FORECAST_MAP_URI)
    assert resource.mime_type == "text/html;profile=mcp-app"
    assert resource.meta["ui"]["csp"] == {"resourceDomains": ["https://tile.openstreetmap.org"]}
    assert 'id="map"' in resource.content
    assert "<!-- WIDGET_STYLE -->" not in resource.content

    result = await mcp.call_tool("show_forecast_map", {"metric": "XC50", "focus_site_id": 133})
    assert result.structuredContent == {
        "date": "2030-01-02", "metric": "XC50", "available_dates": ["2030-01-02"],
        "site_count": 2, "sites_with_forecast": 1, "focus_site_id": 133,
        "map_url": "https://www.parra-glideator.com/?metric=XC50&date=2030-01-02&lat=45.8000&lng=11.7000&zoom=8",
    }
    assert result.meta["sites"][0] == {
        "site_id": 133, "name": "Bassano", "latitude": 45.8, "longitude": 11.7,
        "predictions": [{"date": "2030-01-02", "values": [0.75] * 11}],
    }
    assert result.meta["sites"][1]["predictions"] == []

    missing = await mcp.call_tool("show_forecast_map", {"query_date": "2030-01-03"})
    assert missing.structuredContent["date"] == "2030-01-03"
    assert missing.structuredContent["sites_with_forecast"] == 0


@pytest.mark.asyncio
async def test_plan_trip_exposes_constrained_xc_metric_schema():
    tools = await mcp.list_tools()
    plan_trip = next(tool for tool in tools if tool.name == "plan_trip")

    metric_schema = plan_trip.inputSchema["properties"]["metric"]
    assert metric_schema["enum"] == [
        "XC0",
        "XC10",
        "XC20",
        "XC30",
        "XC40",
        "XC50",
        "XC60",
        "XC70",
        "XC80",
        "XC90",
        "XC100",
    ]
