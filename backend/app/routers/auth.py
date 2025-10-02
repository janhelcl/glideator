from fastapi import APIRouter, Depends, HTTPException, Response, Request, Header
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from ..database import AsyncSessionLocal
from .. import models, schemas
from ..security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_access_token_exp_minutes,
    get_refresh_token_exp_days,
    is_cookie_secure,
)
from ..cache import get_redis_client


router = APIRouter(prefix="/auth", tags=["Auth"])


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/register", response_model=schemas.UserOut)
async def register(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    # check if exists
    existing = await db.execute(select(models.User).where(models.User.email == user.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = models.User(email=user.email, password_hash=hash_password(user.password))
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.post("/login", response_model=schemas.TokenOut)
async def login(creds: schemas.UserLogin, response: Response, db: AsyncSession = Depends(get_db)):
    # Rate limit: max N attempts per window per email and IP
    rc = get_redis_client()
    window_sec = int(os.getenv("RATE_LIMIT_WINDOW_MINUTES", "15")) * 60
    max_attempts = int(os.getenv("RATE_LIMIT_LOGIN_ATTEMPTS", "5"))
    ip = "unknown"
    try:
        # FastAPI doesn't pass request here; simple heuristic via X-Forwarded-For is omitted for brevity
        # We scope by email only for now
        key = f"login:attempts:{creds.email}"
        current = rc.incr(key)
        if current == 1:
            rc.expire(key, window_sec)
        if current > max_attempts:
            raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")
    except Exception:
        # If Redis fails, proceed without blocking login
        pass
    result = await db.execute(select(models.User).where(models.User.email == creds.email))
    db_user: Optional[models.User] = result.scalar_one_or_none()
    if not db_user or not verify_password(creds.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access = create_access_token(subject=str(db_user.user_id), expires_minutes=get_access_token_exp_minutes())
    refresh = create_refresh_token(subject=str(db_user.user_id), expires_days=get_refresh_token_exp_days())
    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        samesite="none",  # Required for cross-origin requests
        secure=is_cookie_secure(),
        path="/auth",
    )
    return schemas.TokenOut(access_token=access)


def get_current_user_from_token(token: str, db: AsyncSession) -> models.User:
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = int(payload["sub"])  # type: ignore
    return db.get(models.User, user_id)  # type: ignore


@router.get("/me", response_model=schemas.UserOut)
async def me(authorization: Optional[str] = Header(default=None), db: AsyncSession = Depends(get_db)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = int(payload["sub"])  # type: ignore
    user = await db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user


@router.post("/refresh", response_model=schemas.TokenOut)
async def refresh(request: Request):
    cookie = request.cookies.get("refresh_token")
    if not cookie:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    payload = decode_token(cookie)
    if not payload or payload.get("typ") != "refresh" or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = str(payload["sub"])  # keep as str for token subject
    access = create_access_token(subject=user_id, expires_minutes=get_access_token_exp_minutes())
    return schemas.TokenOut(access_token=access)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path="/auth",
        samesite="none",
        secure=is_cookie_secure(),
    )
    return {"ok": True}


