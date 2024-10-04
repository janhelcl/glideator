from celery import Celery
from sqlalchemy.orm import sessionmaker
from .database import engine
from .services.predict import generate_and_store_predictions
import os

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@rabbitmq:5672//")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "rpc://")

celery = Celery('app',
                broker=CELERY_BROKER_URL,
                backend=CELERY_RESULT_BACKEND)

# Optional: Celery configuration
celery.conf.update(
    timezone='UTC',
    task_annotations={
        'app.tasks.generate_predictions': {'rate_limit': '10/m'}
    },
)
celery.conf.beat_schedule = {
    'generate-predictions-every-hour': {
        'task': 'app.celery_app.generate_predictions_task',
        'schedule': 3600.0,  # Every hour
    },
}
celery.conf.timezone = 'UTC'

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@celery.task
def generate_predictions_task():
    db = SessionLocal()
    try:
        generate_and_store_predictions(db, 'glideator_model.pth', 'preprocessor.pkl')
    except Exception as e:
        print(f"Error generating predictions: {e}")
    finally:
        db.close()