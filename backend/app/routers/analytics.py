import json
import logging
import os
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, DateTime, Integer, JSON, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from ..bot_detection import detect_known_bot
from ..cache import get_redis_client
from ..database import AsyncSessionLocal, Base

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

RATE_LIMIT_ANALYTICS_WINDOW_MINUTES = "RATE_LIMIT_ANALYTICS_WINDOW_MINUTES"
RATE_LIMIT_ANALYTICS_MAX_PER_IP = "RATE_LIMIT_ANALYTICS_MAX_PER_IP"
RATE_LIMIT_ANALYTICS_MAX_PER_ANONYMOUS_ID = "RATE_LIMIT_ANALYTICS_MAX_PER_ANONYMOUS_ID"
MAX_PROPERTIES_BYTES = 12_000
MAX_PROPERTIES_KEYS = 40


class ProductEvent(Base):
    __tablename__ = "product_events"

    event_id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(80), nullable=False, index=True)
    anonymous_id = Column(String(64), nullable=False, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    path = Column(String(500), nullable=True)
    properties = Column(JSON, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )


class BotEvent(Base):
    __tablename__ = "bot_events"

    event_id = Column(Integer, primary_key=True, index=True)
    bot_name = Column(String(80), nullable=False, index=True)
    event_name = Column(String(80), nullable=False, index=True)
    anonymous_id = Column(String(64), nullable=False, index=True)
    session_id = Column(String(64), nullable=False, index=True)
    path = Column(String(500), nullable=True)
    properties = Column(JSON, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )


class ProductEventCreate(BaseModel):
    event_name: str = Field(
        ...,
        min_length=1,
        max_length=80,
        pattern=r"^[a-z][a-z0-9_]*$",
    )
    anonymous_id: str = Field(..., min_length=8, max_length=64)
    session_id: str = Field(..., min_length=8, max_length=64)
    path: Optional[str] = Field(default=None, max_length=500)
    properties: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_name", "anonymous_id", "session_id")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("value cannot be empty")
        return stripped

    @field_validator("path")
    @classmethod
    def strip_path(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("properties")
    @classmethod
    def validate_properties(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if len(value) > MAX_PROPERTIES_KEYS:
            raise ValueError(f"properties may contain at most {MAX_PROPERTIES_KEYS} keys")
        encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
        if len(encoded.encode("utf-8")) > MAX_PROPERTIES_BYTES:
            raise ValueError(f"properties may contain at most {MAX_PROPERTIES_BYTES} bytes")
        return value


class ProductEventAccepted(BaseModel):
    accepted: Literal[True] = True


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded_for.split(",", 1)[0].strip() if forwarded_for else None
    return client_ip or (request.client.host if request.client else "unknown")


def _apply_analytics_rate_limit(*, ip: str, anonymous_id: str) -> None:
    window_seconds = int(os.getenv(RATE_LIMIT_ANALYTICS_WINDOW_MINUTES, "60")) * 60
    max_per_ip = int(os.getenv(RATE_LIMIT_ANALYTICS_MAX_PER_IP, "2000"))
    max_per_anonymous_id = int(
        os.getenv(RATE_LIMIT_ANALYTICS_MAX_PER_ANONYMOUS_ID, "500")
    )

    try:
        redis_client = get_redis_client()
        keys_and_limits = [
            (f"analytics:event:ip:{ip}", max_per_ip),
            (
                f"analytics:event:anonymous:{anonymous_id}",
                max_per_anonymous_id,
            ),
        ]
        for key, limit in keys_and_limits:
            current = redis_client.incr(key)
            if current == 1:
                redis_client.expire(key, window_seconds)
            if current > limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many analytics events. Try again later.",
                )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Analytics rate limiting unavailable")


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post(
    "/events",
    response_model=ProductEventAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_product_event(
    request: Request,
    payload: ProductEventCreate,
    db: AsyncSession = Depends(get_db),
):
    _apply_analytics_rate_limit(
        ip=_client_ip(request),
        anonymous_id=payload.anonymous_id,
    )

    bot_name = detect_known_bot(request.headers.get("user-agent"))
    common_fields = {
        "event_name": payload.event_name,
        "anonymous_id": payload.anonymous_id,
        "session_id": payload.session_id,
        "path": payload.path,
        "properties": payload.properties,
    }
    event = BotEvent(bot_name=bot_name, **common_fields) if bot_name else ProductEvent(**common_fields)
    db.add(event)
    await db.commit()

    logger.debug(
        "Analytics event accepted event_name=%s anonymous_id=%s session_id=%s bot_name=%s",
        payload.event_name,
        payload.anonymous_id,
        payload.session_id,
        bot_name,
    )
    return ProductEventAccepted()
