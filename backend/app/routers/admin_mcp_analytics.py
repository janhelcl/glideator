from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from ..mcp_analytics import McpToolEvent
from .admin import get_db, require_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


class McpToolUsageRow(BaseModel):
    tool_name: str
    calls: int
    successful_calls: int
    failed_calls: int
    success_rate: float
    avg_duration_ms: float


class AdminMcpAnalyticsResponse(BaseModel):
    window_days: int
    total_calls: int
    successful_calls: int
    failed_calls: int
    success_rate: float
    avg_duration_ms: float
    tools_used: int
    tools: List[McpToolUsageRow]


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(100 * numerator / denominator, 1)


@router.get("/mcp-analytics", response_model=AdminMcpAnalyticsResponse)
async def get_mcp_analytics(
    days: int = Query(default=30, ge=1, le=365),
    _: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    summary = (
        await db.execute(
            select(
                func.count(McpToolEvent.event_id),
                func.count(McpToolEvent.event_id).filter(McpToolEvent.success.is_(True)),
                func.avg(McpToolEvent.duration_ms),
                func.count(func.distinct(McpToolEvent.tool_name)),
            ).where(McpToolEvent.created_at >= cutoff)
        )
    ).one()

    total_calls = int(summary[0] or 0)
    successful_calls = int(summary[1] or 0)
    failed_calls = total_calls - successful_calls

    rows = (
        await db.execute(
            select(
                McpToolEvent.tool_name,
                func.count(McpToolEvent.event_id).label("calls"),
                func.count(McpToolEvent.event_id)
                .filter(McpToolEvent.success.is_(True))
                .label("successful_calls"),
                func.avg(McpToolEvent.duration_ms).label("avg_duration_ms"),
            )
            .where(McpToolEvent.created_at >= cutoff)
            .group_by(McpToolEvent.tool_name)
            .order_by(func.count(McpToolEvent.event_id).desc(), McpToolEvent.tool_name.asc())
        )
    ).all()

    tools = []
    for tool_name, calls, successful, avg_duration_ms in rows:
        calls = int(calls or 0)
        successful = int(successful or 0)
        tools.append(
            McpToolUsageRow(
                tool_name=tool_name,
                calls=calls,
                successful_calls=successful,
                failed_calls=calls - successful,
                success_rate=_rate(successful, calls),
                avg_duration_ms=round(float(avg_duration_ms or 0), 1),
            )
        )

    return AdminMcpAnalyticsResponse(
        window_days=days,
        total_calls=total_calls,
        successful_calls=successful_calls,
        failed_calls=failed_calls,
        success_rate=_rate(successful_calls, total_calls),
        avg_duration_ms=round(float(summary[2] or 0), 1),
        tools_used=int(summary[3] or 0),
        tools=tools,
    )
