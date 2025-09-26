from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from ..database import AsyncSessionLocal
from .. import models, schemas
from ..security import hash_password, verify_password, create_access_token, decode_token


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
async def login(creds: schemas.UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).where(models.User.email == creds.email))
    db_user: Optional[models.User] = result.scalar_one_or_none()
    if not db_user or not verify_password(creds.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(subject=str(db_user.user_id))
    return schemas.TokenOut(access_token=token)


def get_current_user_from_token(token: str, db: AsyncSession) -> models.User:
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    user_id = int(payload["sub"])  # type: ignore
    return db.get(models.User, user_id)  # type: ignore


@router.get("/me", response_model=schemas.UserOut)
async def me(authorization: Optional[str] = None, db: AsyncSession = Depends(get_db)):
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


