import functools
import logging
import time
from typing import Awaitable, Callable, Optional, TypeVar

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from .database import AsyncSessionLocal, Base

logger = logging.getLogger(__name__)

T = TypeVar("T")


class McpToolEvent(Base):
    __tablename__ = "mcp_tool_events"

    event_id = Column(Integer, primary_key=True, index=True)
    tool_name = Column(String(80), nullable=False, index=True)
    success = Column(Boolean, nullable=False, index=True)
    duration_ms = Column(Integer, nullable=False)
    error_type = Column(String(120), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )


async def _record_mcp_tool_event(
    *,
    tool_name: str,
    success: bool,
    duration_ms: int,
    error_type: Optional[str] = None,
) -> None:
    """Persist privacy-minimal MCP usage analytics without affecting the tool call."""
    try:
        async with AsyncSessionLocal() as db:
            db.add(
                McpToolEvent(
                    tool_name=tool_name,
                    success=success,
                    duration_ms=max(0, duration_ms),
                    error_type=error_type,
                )
            )
            await db.commit()
    except Exception:
        logger.exception("Failed to persist MCP analytics event tool_name=%s", tool_name)


def track_mcp_tool(tool_name: str) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Track an async MCP tool call while preserving the tool's public signature."""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            started_at = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
            except Exception as exc:
                duration_ms = round((time.perf_counter() - started_at) * 1000)
                await _record_mcp_tool_event(
                    tool_name=tool_name,
                    success=False,
                    duration_ms=duration_ms,
                    error_type=type(exc).__name__,
                )
                raise

            duration_ms = round((time.perf_counter() - started_at) * 1000)
            await _record_mcp_tool_event(
                tool_name=tool_name,
                success=True,
                duration_ms=duration_ms,
            )
            return result

        return wrapper

    return decorator
