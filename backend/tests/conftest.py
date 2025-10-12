import asyncio
import os
import pytest

from app.database import Base, sync_engine


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True, scope="session")
def test_env_setup():
    os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/glideator")
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
    os.environ.setdefault("RATE_LIMIT_LOGIN_ATTEMPTS", "1000")
    os.environ.setdefault("CORS_ALLOW_ORIGINS", "http://test")
    os.environ.setdefault("JWT_REFRESH_COOKIE_PATH", "/auth")
    Base.metadata.create_all(bind=sync_engine)
    yield


