from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List

from ..database import AsyncSessionLocal
from .. import models, schemas
from .auth import decode_token


router = APIRouter(prefix="/users/me/favorites", tags=["Favorites"])


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


@router.get("", response_model=List[int])
async def list_favorites(authorization: Optional[str] = Header(default=None), db: AsyncSession = Depends(get_db)):
    user_id = require_user_id(authorization)
    result = await db.execute(select(models.UserFavorite.site_id).where(models.UserFavorite.user_id == user_id))
    return [row[0] for row in result.all()]


@router.post("")
async def add_favorite(req: schemas.FavoriteRequest, authorization: Optional[str] = Header(default=None), db: AsyncSession = Depends(get_db)):
    user_id = require_user_id(authorization)
    # Upsert-like behavior: ignore if exists
    existing = await db.get(models.UserFavorite, {"user_id": user_id, "site_id": req.site_id})
    if not existing:
        fav = models.UserFavorite(user_id=user_id, site_id=req.site_id)
        db.add(fav)
        await db.commit()
    return {"ok": True}


@router.delete("/{site_id}")
async def remove_favorite(site_id: int, authorization: Optional[str] = Header(default=None), db: AsyncSession = Depends(get_db)):
    user_id = require_user_id(authorization)
    await db.execute(
        delete(models.UserFavorite).where(
            models.UserFavorite.user_id == user_id,
            models.UserFavorite.site_id == site_id,
        )
    )
    await db.commit()
    return {"ok": True}


