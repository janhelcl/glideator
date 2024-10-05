import os
from datetime import datetime
from celery import Celery, chain
from sqlalchemy.orm import sessionmaker
from .database import engine
from .crud import get_latest_gfs_forecast
from .services.predict import generate_and_store_predictions
import gfs.utils

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
        'task': 'app.celery_app.check_and_trigger_predictions_task',
        'schedule': 3600.0,  # Every hour
    },
}
celery.conf.timezone = 'UTC'

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@celery.task
def check_and_trigger_predictions_task():
    """
    Checks for new data availability and triggers prediction tasks for the next five days if new data is available.
    """
    db = SessionLocal()
    try:
        last_gfs_forecast = get_latest_gfs_forecast(db)
        date, run = gfs.utils.find_latest_forecast_parameters()
        latest_available_gfs_forecast = datetime(year=date.year, month=date.month, day=date.day, hour=run)
        if last_gfs_forecast is None or latest_available_gfs_forecast > last_gfs_forecast:
            delta = gfs.utils.find_delta(run, 12)
            task_chain = chain()
            for i in range(7):
                delta_i = delta + 24 * i
                task_chain |= generate_predictions_task.si(date, run, delta_i)
            task_chain.apply_async()
        else:
            print("No new data available. Skipping prediction tasks.")
    except Exception as e:
        print(f"Error in checking data availability: {e}")
    finally:
        db.close()


@celery.task
def generate_predictions_task(date, run, delta):
    db = SessionLocal()
    try:
        generate_and_store_predictions(db, 'glideator_model.pth', 'preprocessor.pkl', date, run, delta)
    except Exception as e:
        print(f"Error generating predictions: {e}")
    finally:
        db.close()