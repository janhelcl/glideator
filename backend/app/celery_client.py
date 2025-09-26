import os
from celery import Celery


# Minimal Celery client for producers (web) that avoids importing task modules
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

celery = Celery(
    'app',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)


