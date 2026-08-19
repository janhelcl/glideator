from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models
from .admin import get_db, require_admin
from .analytics import BotEvent

router = APIRouter(prefix="/admin", tags=["Admin"])


class BotTrafficRow(BaseModel):
    bot_name: str
    events: int
    visitors: int
    sessions: int


class AdminBotAnalyticsResponse(BaseModel):
    window_days: int
    total_events: int
    unique_visitors: int
    unique_sessions: int
    bot_types: int
    bots: List[BotTrafficRow]


@router.get("/bot-analytics", response_model=AdminBotAnalyticsResponse)
async def get_bot_analytics(
    days: int = Query(default=30, ge=1, le=365),
    _: models.User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    summary = (
        await db.execute(
            select(
                func.count(BotEvent.event_id),
                func.count(func.distinct(BotEvent.anonymous_id)),
                func.count(func.distinct(BotEvent.session_id)),
                func.count(func.distinct(BotEvent.bot_name)),
            ).where(BotEvent.created_at >= cutoff)
        )
    ).one()

    rows = (
        await db.execute(
            select(
                BotEvent.bot_name,
                func.count(BotEvent.event_id).label("events"),
                func.count(func.distinct(BotEvent.anonymous_id)).label("visitors"),
                func.count(func.distinct(BotEvent.session_id)).label("sessions"),
            )
            .where(BotEvent.created_at >= cutoff)
            .group_by(BotEvent.bot_name)
            .order_by(func.count(BotEvent.event_id).desc(), BotEvent.bot_name.asc())
        )
    ).all()

    return AdminBotAnalyticsResponse(
        window_days=days,
        total_events=int(summary[0] or 0),
        unique_visitors=int(summary[1] or 0),
        unique_sessions=int(summary[2] or 0),
        bot_types=int(summary[3] or 0),
        bots=[
            BotTrafficRow(
                bot_name=bot_name,
                events=int(events or 0),
                visitors=int(visitors or 0),
                sessions=int(sessions or 0),
            )
            for bot_name, events, visitors, sessions in rows
        ],
    )
