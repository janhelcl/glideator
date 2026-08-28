import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/glideator")

from app import mcp_analytics


@pytest.mark.asyncio
async def test_track_mcp_tool_records_success_without_arguments(monkeypatch):
    recorded = []

    async def fake_record(**event):
        recorded.append(event)

    monkeypatch.setattr(mcp_analytics, "_record_mcp_tool_event", fake_record)

    @mcp_analytics.track_mcp_tool("example_tool")
    async def example_tool(secret_value: str):
        return f"ok:{secret_value}"

    result = await example_tool("do-not-store")

    assert result == "ok:do-not-store"
    assert len(recorded) == 1
    assert recorded[0]["tool_name"] == "example_tool"
    assert recorded[0]["success"] is True
    assert recorded[0]["error_type"] if "error_type" in recorded[0] else None is None
    assert isinstance(recorded[0]["duration_ms"], int)
    assert "secret_value" not in recorded[0]


@pytest.mark.asyncio
async def test_track_mcp_tool_records_failure_and_reraises(monkeypatch):
    recorded = []

    async def fake_record(**event):
        recorded.append(event)

    monkeypatch.setattr(mcp_analytics, "_record_mcp_tool_event", fake_record)

    @mcp_analytics.track_mcp_tool("broken_tool")
    async def broken_tool():
        raise ValueError("sensitive details")

    with pytest.raises(ValueError, match="sensitive details"):
        await broken_tool()

    assert recorded == [
        {
            "tool_name": "broken_tool",
            "success": False,
            "duration_ms": recorded[0]["duration_ms"],
            "error_type": "ValueError",
        }
    ]
