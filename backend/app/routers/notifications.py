from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from ..database import AsyncSessionLocal
from .. import crud, schemas
from .auth import decode_token


router = APIRouter(prefix="/users/me/notifications", tags=["Notifications"])
subscriptions_router = APIRouter(prefix="/users/me/push-subscriptions", tags=["Notifications"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


def require_user_id(authorization: Optional[str]) -> int:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return int(payload["sub"])  # type: ignore[arg-type]


@router.get("", response_model=List[schemas.NotificationOut])
async def list_notifications(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    user_id = require_user_id(authorization)
    notifications = await crud.list_user_notifications(db, user_id)
    return notifications


@router.post("", response_model=schemas.NotificationOut, status_code=status.HTTP_201_CREATED)
async def create_notification(
    payload: schemas.NotificationCreate,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    user_id = require_user_id(authorization)
    site = await crud.get_site(db, payload.site_id)
    if not site:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    try:
        notification = await crud.create_user_notification(db, user_id, payload)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Notification already exists")
    return notification


@router.patch("/{notification_id}", response_model=schemas.NotificationOut)
async def update_notification(
    notification_id: int,
    payload: schemas.NotificationUpdate,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    user_id = require_user_id(authorization)
    notification = await crud.get_user_notification(db, user_id, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")
    if "site_id" in update_data:
        site = await crud.get_site(db, update_data["site_id"])
        if not site:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    try:
        updated = await crud.update_user_notification(db, notification, payload)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Notification already exists")
    return updated


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    user_id = require_user_id(authorization)
    notification = await crud.get_user_notification(db, user_id, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    await crud.delete_user_notification(db, notification)
    return None


@router.get("/{notification_id}/events", response_model=List[schemas.NotificationEventOut])
async def list_notification_events(
    notification_id: int,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
):
    user_id = require_user_id(authorization)
    notification = await crud.get_user_notification(db, user_id, notification_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    events = await crud.list_notification_events_for_notification(db, notification.notification_id, limit=limit)
    return events


# Separate router for events across all notifications (for catch-up)
events_router = APIRouter(prefix="/users/me/notification-events", tags=["Notifications"])


@events_router.get("", response_model=List[schemas.NotificationEventOut])
async def list_recent_events(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
    since: Optional[datetime] = Query(default=None, description="Only return events after this ISO timestamp"),
    limit: int = Query(default=50, le=100, description="Maximum number of events to return"),
):
    """
    Get recent notification events for the current user across all their notifications.
    Used for catch-up when app opens after being offline.
    """
    user_id = require_user_id(authorization)
    events = await crud.list_recent_notification_events_for_user(db, user_id, since=since, limit=limit)
    return events


@subscriptions_router.get("", response_model=List[schemas.PushSubscriptionOut])
async def list_push_subscriptions(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    user_id = require_user_id(authorization)
    subscriptions = await crud.list_push_subscriptions(db, user_id)
    return subscriptions


@subscriptions_router.post("", response_model=schemas.PushSubscriptionOut, status_code=status.HTTP_201_CREATED)
async def register_push_subscription(
    payload: schemas.PushSubscriptionCreate,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    user_id = require_user_id(authorization)
    try:
        subscription = await crud.upsert_push_subscription(db, user_id, payload)
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Push subscription already exists")
    return subscription


@subscriptions_router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_push_subscription_endpoint(
    subscription_id: int,
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    user_id = require_user_id(authorization)
    subscription = await crud.deactivate_push_subscription(db, user_id, subscription_id)
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return None
