from types import SimpleNamespace

import pytest

from app.routers import admin_mcp_analytics


class FakeResult:
    def __init__(self, *, one=None, all_rows=None):
        self._one = one
        self._all = all_rows

    def one(self):
        return self._one

    def all(self):
        return self._all


class FakeDb:
    def __init__(self):
        self.calls = 0

    async def execute(self, statement):
        self.calls += 1
        if self.calls == 1:
            return FakeResult(one=(10, 9, 125.4, 3))
        return FakeResult(
            all_rows=[
                ("plan_trip", 6, 6, 150.0),
                ("find_sites", 3, 2, 80.0),
                ("get_site_info", 1, 1, 40.0),
            ]
        )


def test_mcp_rate_is_safe_and_rounded():
    assert admin_mcp_analytics._rate(9, 10) == 90.0
    assert admin_mcp_analytics._rate(1, 3) == 33.3
    assert admin_mcp_analytics._rate(0, 0) == 0.0


@pytest.mark.asyncio
async def test_mcp_analytics_aggregates_tool_usage():
    result = await admin_mcp_analytics.get_mcp_analytics(
        days=30,
        _=SimpleNamespace(),
        db=FakeDb(),
    )

    assert result.total_calls == 10
    assert result.successful_calls == 9
    assert result.failed_calls == 1
    assert result.success_rate == 90.0
    assert result.avg_duration_ms == 125.4
    assert result.tools_used == 3
    assert result.tools[0].tool_name == "plan_trip"
    assert result.tools[1].failed_calls == 1
    assert result.tools[1].success_rate == 66.7
