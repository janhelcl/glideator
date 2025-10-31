import os
import time
import asyncio
from datetime import datetime, date
import logging

from celery import Celery, chain
from .database import AsyncSessionLocal
from .crud import get_latest_gfs_forecast, delete_similar_dates_by_forecast_date, create_similar_date
from .services.forecast import process_forecasts, fetch_sites, WEATHER_FEATURES, SITE_FEATURES, DATE_FEATURES
from .services.d2d_similarity import (
    load_scaler,
    extract_features_from_forecast,
    find_similar_days,
    get_past_scaled_features,
    reconstruct_forecast_from_unscaled_features,
)
from .services.notifications import evaluate_and_queue_notifications
from .models import Prediction, Forecast, SimilarDate
from . import schemas
import gfs.utils
import gfs.fetch
import net.preprocessing as preprocessing
import json
import pandas as pd
import numpy as np
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
    acks_late=True,
    task_reject_on_worker_lost=True,
    task_acks_on_failure_or_timeout=False,
    task_publish_retry=True,
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
    'evaluate-notifications-hourly': {
        'task': 'app.celery_app.dispatch_notifications',
        'schedule': 1800.0,  # Every 30 minutes
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
    Chains process_forecasts_task and then find_and_save_similar_days_task.
    """
    # https://blog.det.life/replacing-celery-tasks-inside-a-chain-b1328923fb02
    forecasts = []
    for delta in deltas:
        forecast = gfs.fetch.get_gfs_data(date, run, delta, lat_gfs, lon_gfs, source='grib')
        forecasts.append(forecast.reset_index().to_dict())
        if delta != deltas[-1]:
            time.sleep(10)
    # Chain: process forecasts -> find similar days
    chain(process_forecasts_task.s(forecasts), find_and_save_similar_days_task.s()).apply_async()


async def _process_forecasts_async(forecasts):
    """
    Async version of process forecasts.
    Returns the forecast_date and joined_forecasts for use by subsequent tasks.
    """
    async with AsyncSessionLocal() as db:
        # Reconstruct joined_forecasts before processing (we need it for similarity search)
        import pandas as pd
        from .services.forecast import validate_forecasts, join_forecasts
        
        forecast_dfs = [
            pd.DataFrame.from_records(forecast).set_index(['lat', 'lon'])
            for forecast in forecasts
        ]
        validate_forecasts(forecast_dfs)
        joined_forecasts = (
            join_forecasts(forecast_dfs)
            .rename_axis(index={'lat': 'lat_gfs', 'lon': 'lon_gfs'})
        )
        joined_forecasts['ref_time'] = joined_forecasts['ref_time_12']
        # Use ref_time (the date the forecast is for) instead of date_12
        forecast_date = joined_forecasts['ref_time'].iloc[0].date()
        
        # Now process forecasts (this will save predictions and Forecast records)
        result = await process_forecasts(db, forecasts)
        try:
            events = await evaluate_and_queue_notifications(db)
            if events:
                logger.info("Queued %s notification events after forecast processing", len(events))
        except Exception as exc:
            logger.error("Failed to evaluate notifications after forecasts: %s", exc, exc_info=True)
        
        # Extract metadata
        run = joined_forecasts['run_12'].iloc[0]
        gfs_forecast_at = datetime(year=forecast_date.year if isinstance(forecast_date, date) else forecast_date.year,
                                   month=forecast_date.month if isinstance(forecast_date, date) else forecast_date.month,
                                   day=forecast_date.day if isinstance(forecast_date, date) else forecast_date.day,
                                   hour=run)
        
        # Return both date and joined_forecasts (convert to dict for Celery serialization)
        # Note: joined_forecasts is large, so we serialize it
        joined_forecasts_reset = joined_forecasts.reset_index()
        return {
            'forecast_date': forecast_date,
            'joined_forecasts': joined_forecasts_reset.to_dict('records'),
            'computed_at': datetime.now(),
            'gfs_forecast_at': gfs_forecast_at
        }


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


async def _dispatch_notifications_async():
    async with AsyncSessionLocal() as db:
        try:
            logger.info("Running scheduled notification evaluation...")
            events = await evaluate_and_queue_notifications(db)
            if events:
                logger.info("Queued %s notification events via scheduled task", len(events))
            else:
                logger.info("Scheduled notification evaluation complete: no events generated")
        except Exception as exc:
            logger.error("Failed to evaluate notifications: %s", exc, exc_info=True)


@celery.task
def dispatch_notifications():
    return run_async(_dispatch_notifications_async())


async def _find_and_save_similar_days_async(forecast_date, joined_forecasts_records, computed_at, gfs_forecast_at):
    """
    Async version of find and save similar days.
    After forecasts are processed, find K most similar past days for each site.
    Uses the raw joined_forecasts data for accurate feature extraction.
    """
    async with AsyncSessionLocal() as db:
        try:
            # Get K from environment variable, default 5
            top_k = int(os.getenv("D2D_SIMILAR_DAYS_K", "5"))
            
            logger.info(f"Finding similar days for forecast_date {forecast_date} with K={top_k}")
            
            # Delete existing similar_dates for this forecast_date (overwrite behavior)
            await delete_similar_dates_by_forecast_date(db, forecast_date)
            
            # Load scaler
            scaler = load_scaler()
            
            # Reconstruct joined_forecasts DataFrame from records
            joined_forecasts_df = pd.DataFrame(joined_forecasts_records)
            joined_forecasts_df = joined_forecasts_df.set_index(['lat_gfs', 'lon_gfs'])
            
            # Get all sites
            sites_df = await fetch_sites(db)
            
            # Process each site
            sites_processed = 0
            sites_with_similar_days = 0
            
            for _, site_row in sites_df.iterrows():
                site_id = site_row['site_id']
                lat_gfs = site_row['lat_gfs']
                lon_gfs = site_row['lon_gfs']
                site_lat = site_row['latitude']
                site_lon = site_row['longitude']
                site_alt = site_row['altitude']
                
                # Get row from joined_forecasts for this site's coordinates
                try:
                    row = joined_forecasts_df.loc[(lat_gfs, lon_gfs)]
                except KeyError:
                    logger.debug(f"No forecast found for site_id {site_id} at ({lat_gfs}, {lon_gfs})")
                    continue
                
                # Extract features from raw forecast data (exact match with WEATHER_FEATURES)
                features = extract_features_from_forecast(
                    row,
                    site_lat,
                    site_lon,
                    site_alt,
                    forecast_date
                )
                
                # Scale features
                scaled_features = scaler.transform(features.reshape(1, -1))[0]
                
                # Find similar days
                similar_days = await find_similar_days(db, site_id, scaled_features, top_k)
                
                if not similar_days:
                    logger.debug(f"No similar days found for site_id {site_id}")
                    sites_processed += 1
                    continue
                
                # Get forecast record for metadata (computed_at, gfs_forecast_at)
                from .crud import get_forecast
                forecast_record = await get_forecast(db, forecast_date, lat_gfs, lon_gfs)
                if not forecast_record:
                    logger.warning(f"No forecast record found for forecast_date {forecast_date} at ({lat_gfs}, {lon_gfs}), skipping metadata")
                    sites_processed += 1
                    continue
                
                # For each similar day, unscale the features and reconstruct forecast
                for past_date, similarity in similar_days:
                    # Get unscaled features from scaled_features table (these ARE the past forecast)
                    unscaled_features = await get_past_scaled_features(db, site_id, past_date)
                    
                    if unscaled_features is None:
                        logger.warning(f"No scaled features found for site_id {site_id}, past_date {past_date}")
                        continue
                    
                    # Reconstruct forecast JSON from unscaled features
                    try:
                        forecast_dict = reconstruct_forecast_from_unscaled_features(unscaled_features)
                        
                        # Create similar_date record with reconstructed forecasts
                        similar_date = schemas.SimilarDateCreate(
                            site_id=site_id,
                            forecast_date=forecast_date,
                            past_date=past_date,
                            similarity=similarity,
                            forecast_9=json.dumps(forecast_dict['forecast_9']),
                            forecast_12=json.dumps(forecast_dict['forecast_12']),
                            forecast_15=json.dumps(forecast_dict['forecast_15']),
                            computed_at=forecast_record.computed_at,
                            gfs_forecast_at=forecast_record.gfs_forecast_at
                        )
                        
                        await create_similar_date(db, similar_date)
                        logger.debug(f"Saved similar_date for site_id {site_id}, forecast_date {forecast_date}, past_date {past_date}")
                    except Exception as e:
                        logger.error(f"Error reconstructing forecast for site_id {site_id}, past_date {past_date}: {e}", exc_info=True)
                        continue
                
                sites_processed += 1
                sites_with_similar_days += 1
            
            logger.info(f"Processed {sites_processed} sites for forecast_date {forecast_date}")
            
        except Exception as e:
            logger.error(f"Error in finding similar days: {e}", exc_info=True)
            raise


@celery.task
def find_and_save_similar_days_task(process_result):
    """
    Find and save similar days after forecasts are processed.
    Receives result from process_forecasts_task which includes forecast_date and joined_forecasts.
    """
    if not isinstance(process_result, dict):
        logger.error("process_result is not a dict, cannot find similar days")
        return
    
    forecast_date = process_result.get('forecast_date')
    joined_forecasts = process_result.get('joined_forecasts')
    
    if not forecast_date or not joined_forecasts:
        logger.error("Missing forecast_date or joined_forecasts in process_result")
        return
    
    # Extract metadata from process_result if available
    computed_at = process_result.get('computed_at', datetime.now())
    gfs_forecast_at = process_result.get('gfs_forecast_at')
    
    return run_async(_find_and_save_similar_days_async(forecast_date, joined_forecasts, computed_at, gfs_forecast_at))


@celery.task(name="app.celery_app.simple_test_task")
def simple_test_task(message: str):
    logger.info(f"WORKER RECEIVED simple_test_task with message: {message}")
    print(f"WORKER PRINT: simple_test_task with message: {message}") # Add print for extra visibility
    return f"Acknowledged: {message}"
