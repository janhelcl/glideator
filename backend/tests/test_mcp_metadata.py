import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/glideator")

from app import schemas
from app.mcp import _normalize_site_name, mcp


EXPECTED_TOOLS = {
    "find_sites",
    "list_sites",
    "get_site_info",
    "get_site_resources",
    "get_site_seasonal_stats",
    "get_site_predictions",
    "get_site_takeoffs_and_landings",
    "plan_trip",
}


def test_mcp_uses_stateless_json_http_transport():
    assert mcp.settings.stateless_http is True
    assert mcp.settings.json_response is True


def test_site_search_normalization_is_accent_insensitive():
    assert _normalize_site_name("Rana") == _normalize_site_name("Raná")
    assert _normalize_site_name("  KÖSSEN ") == _normalize_site_name("Kossen")


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
