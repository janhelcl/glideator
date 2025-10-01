import os
from typing import Optional

from redis import Redis

_redis_client: Optional[Redis] = None


def get_redis_url() -> str:
    return (
        os.getenv("REDIS_URL")
        or os.getenv("CELERY_BROKER_URL")
        or "redis://redis:6379/0"
    )


def get_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(get_redis_url(), decode_responses=True)
    return _redis_client


