import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..cache import get_redis_client
from ..database import AsyncSessionLocal
from .. import models, schemas
from .auth import decode_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["Feedback"])

RATE_LIMIT_FEEDBACK_WINDOW_MINUTES = "RATE_LIMIT_FEEDBACK_WINDOW_MINUTES"
RATE_LIMIT_FEEDBACK_MAX_PER_IP = "RATE_LIMIT_FEEDBACK_MAX_PER_IP"
RATE_LIMIT_FEEDBACK_MAX_PER_USER = "RATE_LIMIT_FEEDBACK_MAX_PER_USER"


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded_for.split(",", 1)[0].strip() if forwarded_for else None
    return client_ip or (request.client.host if request.client else "unknown")


def _apply_feedback_rate_limit(*, ip: str, user_id: int) -> None:
    window_sec = int(os.getenv(RATE_LIMIT_FEEDBACK_WINDOW_MINUTES, "60")) * 60
    max_ip = int(os.getenv(RATE_LIMIT_FEEDBACK_MAX_PER_IP, "10"))
    max_user = int(os.getenv(RATE_LIMIT_FEEDBACK_MAX_PER_USER, "10"))
    try:
        rc = get_redis_client()
        keys_limits = [
            (f"feedback:submit:ip:{ip}", max_ip),
            (f"feedback:submit:user:{user_id}", max_user),
        ]
        for key, max_count in keys_limits:
            current = rc.incr(key)
            if current == 1:
                rc.expire(key, window_sec)
            if current > max_count:
                raise HTTPException(
                    status_code=429,
                    detail="Too many feedback submissions. Try again later.",
                )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Feedback rate limiting unavailable")


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


def require_user_id(authorization: Optional[str]) -> int:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        return int(payload["sub"])  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/submit", response_model=schemas.FeedbackCreated)
async def submit_feedback(
    request: Request,
    payload: schemas.FeedbackCreate,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    user_id = require_user_id(authorization)
    _apply_feedback_rate_limit(ip=_client_ip(request), user_id=user_id)
    row = models.FeedbackSubmission(
        message=payload.message,
        user_id=user_id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    logger.info("Feedback submitted id=%s user_id=%s", row.id, user_id)
    return schemas.FeedbackCreated()
