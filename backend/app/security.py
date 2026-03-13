from datetime import datetime, timedelta, timezone
import uuid
from typing import Optional

from jose import jwt
from passlib.context import CryptContext
import os


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def get_app_env() -> str:
    return os.getenv("APP_ENV", os.getenv("ENV", "development")).strip().lower()


def is_production() -> bool:
    return get_app_env() in {"prod", "production"}


def get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET_KEY")
    if secret:
        return secret
    if is_production():
        raise RuntimeError("JWT_SECRET_KEY must be set in production")
    # Development-only fallback for local iteration.
    return "dev-insecure-secret-change-me"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(subject: str, expires_minutes: int = 15) -> str:
    to_encode = {
        "sub": subject,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(to_encode, get_jwt_secret(), algorithm="HS256")


def create_refresh_token(subject: str, expires_days: int = 30) -> str:
    to_encode = {
        "sub": subject,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=expires_days),
        "typ": "refresh",
    }
    return jwt.encode(to_encode, get_jwt_secret(), algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, get_jwt_secret(), algorithms=["HS256"])  # type: ignore
    except Exception:
        return None


def get_access_token_exp_minutes() -> int:
    try:
        return int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    except Exception:
        return 15


def get_refresh_token_exp_days() -> int:
    try:
        return int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30"))
    except Exception:
        return 30


def is_cookie_secure() -> bool:
    value = os.getenv("JWT_COOKIE_SECURE")
    if value is not None:
        return value.lower() == "true"
    return is_production()


