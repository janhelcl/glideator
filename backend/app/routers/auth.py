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
    normalize_email,
)
from ..cache import get_redis_client


router = APIRouter(prefix="/auth", tags=["Auth"])


RATE_LIMIT_WINDOW_MINUTES = "RATE_LIMIT_WINDOW_MINUTES"
RATE_LIMIT_LOGIN_ATTEMPTS = "RATE_LIMIT_LOGIN_ATTEMPTS"
RATE_LIMIT_REGISTER_ATTEMPTS = "RATE_LIMIT_REGISTER_ATTEMPTS"


def apply_attempt_rate_limit(action: str, *, email: str, ip: str, max_attempts_env: str, default_attempts: str) -> None:
    rc = get_redis_client()
    window_sec = int(os.getenv(RATE_LIMIT_WINDOW_MINUTES, "15")) * 60
    max_attempts = int(os.getenv(max_attempts_env, default_attempts))
    try:
        keys = [
            f"{action}:attempts:email:{email}",
            f"{action}:attempts:ip:{ip}",
            f"{action}:attempts:email-ip:{email}:{ip}",
        ]
        for key in keys:
            current = rc.incr(key)
            if current == 1:
                rc.expire(key, window_sec)
            if current > max_attempts:
                raise HTTPException(status_code=429, detail="Too many attempts. Try again later.")
    except HTTPException:
        raise
    except Exception:
        # If Redis fails, proceed without blocking auth, but log it loudly.
        import logging
        logging.getLogger(__name__).exception("Rate limiting unavailable for %s", action)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.post("/register", response_model=schemas.UserOut)
async def register(user: schemas.UserCreate, request: Request, db: AsyncSession = Depends(get_db)):
    email = normalize_email(user.email)
    forwarded_for = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded_for.split(",", 1)[0].strip() if forwarded_for else None
    ip = client_ip or (request.client.host if request.client else "unknown")
    apply_attempt_rate_limit(
        "register",
        email=email,
        ip=ip,
        max_attempts_env=RATE_LIMIT_REGISTER_ATTEMPTS,
        default_attempts="5",
    )

    existing = await db.execute(select(models.User).where(models.User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    db_user = models.User(email=email, password_hash=hash_password(user.password))
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


@router.post("/login", response_model=schemas.TokenOut)
async def login(
    creds: schemas.UserLogin,
    response: Response,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    forwarded_for = request.headers.get("x-forwarded-for", "")
    client_ip = forwarded_for.split(",", 1)[0].strip() if forwarded_for else None
    ip = client_ip or (request.client.host if request.client else "unknown")
    email = normalize_email(creds.email)
    apply_attempt_rate_limit(
        "login",
        email=email,
        ip=ip,
        max_attempts_env=RATE_LIMIT_LOGIN_ATTEMPTS,
        default_attempts="5",
    )
    result = await db.execute(select(models.User).where(models.User.email == email))
    db_user: Optional[models.User] = result.scalar_one_or_none()
    if not db_user or not verify_password(creds.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access = create_access_token(subject=str(db_user.user_id), expires_minutes=get_access_token_exp_minutes())
    refresh_days = get_refresh_token_exp_days()
    refresh = create_refresh_token(subject=str(db_user.user_id), expires_days=refresh_days)
    cookie_path = os.getenv("JWT_REFRESH_COOKIE_PATH", "/auth")
    response.set_cookie(
        key="refresh_token",
        value=refresh,
        httponly=True,
        samesite="lax",  # Using Lax since frontend proxies requests (same-origin)
        secure=is_cookie_secure(),
        path=cookie_path,
        max_age=refresh_days * 24 * 60 * 60,  # Convert days to seconds for cookie persistence
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
async def refresh(request: Request, db: AsyncSession = Depends(get_db)):
    cookie = request.cookies.get("refresh_token")
    if not cookie:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    payload = decode_token(cookie)
    if not payload or payload.get("typ") != "refresh" or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user_id = int(payload["sub"])
    user = await db.get(models.User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    access = create_access_token(subject=str(user_id), expires_minutes=get_access_token_exp_minutes())
    return schemas.TokenOut(access_token=access)


@router.post("/logout")
async def logout(response: Response):
    cookie_path = os.getenv("JWT_REFRESH_COOKIE_PATH", "/auth")
    response.delete_cookie(
        key="refresh_token",
        path=cookie_path,
        samesite="lax",
        secure=is_cookie_secure(),
    )
    return {"ok": True}


