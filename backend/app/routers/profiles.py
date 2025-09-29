from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from ..database import AsyncSessionLocal
from .. import models, schemas
from .auth import decode_token


router = APIRouter(prefix="/users/me", tags=["Profiles"])


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
    return int(payload["sub"])  # type: ignore


@router.get("/profile", response_model=schemas.UserProfileOut)
async def get_profile(authorization: Optional[str] = Header(default=None), db: AsyncSession = Depends(get_db)):
    user_id = require_user_id(authorization)
    result = await db.execute(select(models.UserProfile).where(models.UserProfile.user_id == user_id))
    profile = result.scalar_one_or_none()
    if not profile:
        # Return defaults
        return schemas.UserProfileOut(
            user_id=user_id,
            display_name=None,
            home_lat=None,
            home_lon=None,
            preferred_metric='XC0',
        )
    return schemas.UserProfileOut(
        user_id=user_id,
        display_name=profile.display_name,
        home_lat=profile.home_lat,
        home_lon=profile.home_lon,
        preferred_metric=profile.preferred_metric,
    )


@router.patch("/profile", response_model=schemas.UserProfileOut)
async def update_profile(payload: schemas.UserProfileUpdate, authorization: Optional[str] = Header(default=None), db: AsyncSession = Depends(get_db)):
    user_id = require_user_id(authorization)
    profile = await db.get(models.UserProfile, user_id)
    if not profile:
        profile = models.UserProfile(user_id=user_id)
        db.add(profile)
    if payload.display_name is not None:
        profile.display_name = payload.display_name
    if payload.home_lat is not None:
        profile.home_lat = payload.home_lat
    if payload.home_lon is not None:
        profile.home_lon = payload.home_lon
    if payload.preferred_metric is not None:
        profile.preferred_metric = payload.preferred_metric
    await db.commit()
    await db.refresh(profile)
    return schemas.UserProfileOut(
        user_id=user_id,
        display_name=profile.display_name,
        home_lat=profile.home_lat,
        home_lon=profile.home_lon,
        preferred_metric=profile.preferred_metric,
    )


