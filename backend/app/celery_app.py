import os
import time
from datetime import datetime
import logging

from celery import Celery, chain
from sqlalchemy.orm import sessionmaker
from .database import engine
from .crud import get_latest_gfs_forecast
from .services.forecast import process_forecasts, fetch_sites
import gfs.utils
import gfs.fetch


logger = logging.getLogger(__name__)


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
        'task': 'app.celery_app.check_and_trigger_forecast_processing',
        'schedule': 3600.0,  # Every hour
    },
}
celery.conf.timezone = 'UTC'

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@celery.task
def check_and_trigger_forecast_processing():
    """
    Checks for new data availability and triggers forecast processing if new data is available.
    """
    db = SessionLocal()
    try:
        last_gfs_forecast = get_latest_gfs_forecast(db)
        date, run = gfs.utils.find_latest_forecast_parameters()
        latest_available_gfs_forecast = datetime(year=date.year, month=date.month, day=date.day, hour=run)
        if last_gfs_forecast is None or latest_available_gfs_forecast > last_gfs_forecast:
            logger.info("New data available. Triggering forecast processing.")
            # find deltas
            delta = gfs.utils.find_delta(run, 9)
            delta_9s = [delta + 24 * i for i in range(7)]
            all_deltas = [[delta_9, delta_9 + 3, delta_9 + 6] for delta_9 in delta_9s]
            # fetch sites and prepare coordinates
            points = fetch_sites(db).drop_duplicates(subset=['lat_gfs', 'lon_gfs'])
            lat_gfs = points['lat_gfs'].values.tolist()
            lon_gfs = points['lon_gfs'].values.tolist()
            # fetch forecasts
            tasks = []
            for deltas in all_deltas:
                task = fetch_forecast_for_day_task.si(date, run, deltas, lat_gfs, lon_gfs)
                tasks.append(task)
                if deltas != all_deltas[-1]:  # Don't sleep after the last task
                    tasks.append(sleep_task.si(10))  # Use the defined sleep_task
            chain(*tasks).apply_async()
        else:
            logger.info("No new data available. Skipping prediction tasks.")
    except Exception as e:
        logger.error(f"Error in checking data availability: {e}")
    finally:
        db.close()


@celery.task
def sleep_task(duration):
    """
    Sleeps for a specified duration in seconds.
    """
    time.sleep(duration)


@celery.task
def fetch_forecast_for_day_task(date, run, deltas, lat_gfs, lon_gfs):
    """
    Fetches and processes GFS grib files for a given day.
    """
    # https://blog.det.life/replacing-celery-tasks-inside-a-chain-b1328923fb02
    forecasts = []
    for delta in deltas:
        forecast = gfs.fetch.get_gfs_data(date, run, delta, lat_gfs, lon_gfs, source='grib')
        forecasts.append(forecast.reset_index().to_dict())
        if delta != deltas[-1]:
            time.sleep(10)
    process_forecasts_task.delay(forecasts)


@celery.task
def process_forecasts_task(forecasts):
    with SessionLocal() as db:
        return process_forecasts(db, forecasts)
