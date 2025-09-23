import os
import time
import asyncio
from datetime import datetime, date
import logging

from celery import Celery, chain
from .database import AsyncSessionLocal
from .crud import get_latest_gfs_forecast
from .services.forecast import process_forecasts, fetch_sites
from .models import Prediction, Forecast
import gfs.utils
import gfs.fetch
from sqlalchemy import and_, select, delete
from celery.schedules import crontab


logger = logging.getLogger(__name__)


CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/1")

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
    'cleanup-old-data-daily': {
        'task': 'app.celery_app.cleanup_old_data',
        'schedule': crontab(hour=2, minute=0),  # Every day at 2 AM
    },
}
celery.conf.timezone = 'UTC'


def run_async(coro):
    """Helper function to run async functions in Celery tasks"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # If we're already in an async context, we need to create a new event loop
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return loop.run_until_complete(coro)


async def _check_and_trigger_forecast_processing_async():
    """
    Async version of forecast processing check.
    """
    async with AsyncSessionLocal() as db:
        try:
            last_gfs_forecast = await get_latest_gfs_forecast(db)
            date, run = gfs.utils.find_latest_forecast_parameters()
            latest_available_gfs_forecast = datetime(year=date.year, month=date.month, day=date.day, hour=run)
            if last_gfs_forecast is None or latest_available_gfs_forecast > last_gfs_forecast:
                logger.info("New data available. Triggering forecast processing.")
                # find deltas
                delta = gfs.utils.find_delta(run, 9)
                delta_9s = [delta + 24 * i for i in range(7)]
                all_deltas = [[delta_9, delta_9 + 3, delta_9 + 6] for delta_9 in delta_9s]
                # fetch sites and prepare coordinates
                points = await fetch_sites(db)
                points = points.drop_duplicates(subset=['lat_gfs', 'lon_gfs'])
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


@celery.task
def check_and_trigger_forecast_processing():
    """
    Checks for new data availability and triggers forecast processing if new data is available.
    """
    return run_async(_check_and_trigger_forecast_processing_async())


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


async def _process_forecasts_async(forecasts):
    """
    Async version of process forecasts.
    """
    async with AsyncSessionLocal() as db:
        return await process_forecasts(db, forecasts)


async def _cleanup_old_data_async():
    """
    Async version of cleanup old data.
    """
    today = date.today()
    async with AsyncSessionLocal() as db:
        try:
            # Delete old predictions
            await db.execute(
                delete(Prediction).where(Prediction.date < today)
            )
            
            # Delete old forecasts
            await db.execute(
                delete(Forecast).where(Forecast.date < today)
            )
            
            await db.commit()
            logger.info(f"Cleaned up predictions and forecasts older than {today}")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            await db.rollback()
            raise


@celery.task
def process_forecasts_task(forecasts):
    return run_async(_process_forecasts_async(forecasts))


@celery.task
def cleanup_old_data():
    """
    Deletes all predictions and forecasts older than today.
    """
    return run_async(_cleanup_old_data_async())

@celery.task(name="app.celery_app.simple_test_task")
def simple_test_task(message: str):
    logger.info(f"WORKER RECEIVED simple_test_task with message: {message}")
    print(f"WORKER PRINT: simple_test_task with message: {message}") # Add print for extra visibility
    return f"Acknowledged: {message}"
