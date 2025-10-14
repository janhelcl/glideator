import os
import logging
from datetime import datetime
from pathlib import Path
import json

import torch
import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from .. import crud, schemas, models
import gfs.fetch
import net.io
import net.preprocessing as preprocessing
from gfs.constants import HPA_LVLS


logger = logging.getLogger(__name__)


# Global model cache to avoid reloading on every prediction
_MODEL_CACHE = None


def get_model():
    """
    Get the PyTorch model, loading it once and caching for subsequent calls.
    This prevents memory spikes from repeatedly loading the ~400MB model.
    """
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        logger.info(f"Loading PyTorch model from {MODEL_PATH}...")
        _MODEL_CACHE = torch.load(MODEL_PATH, map_location='cpu')
        logger.info("Model loaded successfully and cached in memory")
    return _MODEL_CACHE


EXPECTED_COLUMNS = [
    *gfs.fetch.get_col_order(),
    'date',
    'run',
    'delta',
    'ref_time'
]
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_FILENAME = 'model.pth'
MODEL_PATH = BASE_DIR / 'models' / MODEL_FILENAME
REFERENCES = (
    (6, 3),
    (12, 0),
    (12, 3)
)
WEATHER_FEATURES = []
for run, delta in REFERENCES:
    for col in gfs.fetch.get_col_order():
        WEATHER_FEATURES.append(f'{col}_{run+delta}')
SITE_FEATURES = ['latitude', 'longitude', 'altitude']
SITE_ID = 'site_id'
DATE_FEATURES = ['weekend', 'year', 'day_of_year_sin', 'day_of_year_cos']


async def process_forecasts(db: AsyncSession, forecasts):
    # reconstruct dfs
    forecasts = [
        pd.DataFrame.from_records(forecast).set_index(['lat', 'lon'])
        for forecast in forecasts
    ]
    # prepare dataset
    validate_forecasts(forecasts)
    joined_forecasts = (
        join_forecasts(forecasts)
        .rename_axis(index={'lat': 'lat_gfs', 'lon': 'lon_gfs'})
    )
    joined_forecasts['ref_time'] = joined_forecasts['ref_time_12']
    # prepare metadata
    computed_at = datetime.now()
    date = joined_forecasts['date_12'].iloc[0]
    run = joined_forecasts['run_12'].iloc[0]
    gfs_forecast_at = datetime(year=date.year, month=date.month, day=date.day, hour=run)
    # score and save
    await get_and_save_predictions(db, joined_forecasts, computed_at, gfs_forecast_at)
    await process_and_save_forecasts(db, joined_forecasts, computed_at, gfs_forecast_at)
    await db.commit() # commit both together


async def fetch_sites(db: AsyncSession):
    sites = await crud.get_sites(db, limit=1000)
    sites_df = pd.DataFrame([
        {
            'site_id': site.site_id,
            'latitude': site.latitude,
            'longitude': site.longitude,
            'altitude': site.altitude,
            'lat_gfs': site.lat_gfs,
            'lon_gfs': site.lon_gfs
        } for site in sites
    ])
    return sites_df


def validate_forecasts(forecasts):
    assert len(forecasts) == 3, "Expected 3 forecasts, got {}".format(len(forecasts))
    for forecast in forecasts:
        assert isinstance(forecast, pd.DataFrame), "Expected pd.DataFrame, got {}".format(type(forecast))
        assert forecast.isna().sum().sum() == 0, "Expected no NaNs, got {}".format(forecast.isna().sum().sum())
        assert set(forecast.columns) == set(EXPECTED_COLUMNS), "Expected columns {}, got {}".format(EXPECTED_COLUMNS, forecast.columns)
    dates = set(forecast['date'].unique()[0] for forecast in forecasts)
    assert len(dates) == 1, "Expected 1 date, got {}".format(len(dates))
    ref_hours = set(forecast['ref_time'].dt.hour.unique()[0] for forecast in forecasts)
    assert ref_hours == {9, 12, 15}, "Expected ref_time hours to be 9, 12, 15, got {}".format(ref_hours)
    shapes = set(forecast.shape for forecast in forecasts)
    assert len(shapes) == 1, "Expected all forecasts to have the same shape, got {}".format(shapes)
    runs = set(forecast['run'].unique()[0] for forecast in forecasts)
    assert len(runs) == 1, "Expected all forecasts to have the same run, got {}".format(runs)


def _rename_columns(forecast):
    hour = forecast['ref_time'].iloc[0].hour
    return forecast.rename(columns={col: f"{col}_{hour}" for col in forecast.columns})


def join_forecasts(forecasts):
    forecasts = [_rename_columns(forecast) for forecast in forecasts]
    joined = pd.concat(forecasts, axis=1)
    return joined


async def get_and_save_predictions(db, joined_forecasts, computed_at, gfs_forecast_at):
    # prepare data
    sites = (
        await fetch_sites(db)
    ).set_index(['lat_gfs', 'lon_gfs'])
    full_data = preprocessing.add_date_features(joined_forecasts.join(sites), date_col='ref_time')
    # score
    predictions = net.io.score(
        net=get_model(),
        full_df=full_data, 
        weather_features=WEATHER_FEATURES, 
        site_features=SITE_FEATURES, 
        date_features=DATE_FEATURES, 
        site_id_col=SITE_ID, 
        date_col='ref_time',
        output_mode='records'
    )
    # save
    for site_id, pred_date, metric, value in predictions:
        prediction = schemas.PredictionCreate(
            site_id=site_id,
            date=pred_date,
            metric=metric,
            value=value,
            computed_at=computed_at,
            gfs_forecast_at=gfs_forecast_at
        )
        # Delete existing predictions if any
        await db.execute(
            delete(models.Prediction).where(
                models.Prediction.site_id == site_id,
                models.Prediction.date == pred_date,
                models.Prediction.metric == metric
            )
        )
        # Create new prediction
        await crud.create_prediction(db, prediction)

async def process_and_save_forecasts(db: AsyncSession, joined_forecasts, computed_at, gfs_forecast_at):
    joined_forecasts = joined_forecasts.reset_index()
    forecasts = []
    for _, row in joined_forecasts.iterrows():
        forecast = schemas.ForecastCreate(
            date=row['ref_time'].date(),
            computed_at=computed_at,
            gfs_forecast_at=gfs_forecast_at,
            lat_gfs=row['lat_gfs'],
            lon_gfs=row['lon_gfs'],
            forecast_9=json.dumps(forecast_to_dict(row, suffix='_9')),
            forecast_12=json.dumps(forecast_to_dict(row, suffix='_12')),
            forecast_15=json.dumps(forecast_to_dict(row, suffix='_15'))
        )
        forecasts.append(forecast)
    
    # Delete existing forecasts for the same date
    await crud.delete_forecasts_by_date(db, forecasts[0].date)
    
    # Create new forecasts
    for forecast in forecasts:
        await crud.create_forecast(db, forecast)
    
    await db.commit()

def forecast_to_dict(row, suffix=''):
    geo_iso_cols = [f'geopotential_height_{int(lvl)}hpa_m{suffix}' for lvl in HPA_LVLS]
    temp_iso_cols = [f'temperature_{int(lvl)}hpa_k{suffix}' for lvl in HPA_LVLS]
    humidity_iso_cols = [f'relative_humidity_{int(lvl)}hpa_pct{suffix}' for lvl in HPA_LVLS]
    u_wind_iso_cols = [f'u_wind_{int(lvl)}hpa_ms{suffix}' for lvl in HPA_LVLS]
    v_wind_iso_cols = [f'v_wind_{int(lvl)}hpa_ms{suffix}' for lvl in HPA_LVLS]

    forecast_dict = {
        'hpa_lvls': HPA_LVLS.tolist(),
        'geopotential_height_iso_m': row[geo_iso_cols].values.tolist(),
        'temperature_iso_c': (row[temp_iso_cols] - 273.15).tolist(),
        'relative_humidity_iso_pct': row[humidity_iso_cols].tolist()
    }
    forecast_dict['dewpoint_iso_c'] = calculate_dewpoint(
        forecast_dict['temperature_iso_c'],
        forecast_dict['relative_humidity_iso_pct']
    ).tolist()
    wind_speed, wind_direction = calculate_wind_speed_and_direction(
        row[u_wind_iso_cols].values,
        row[v_wind_iso_cols].values
    )
    forecast_dict['wind_speed_iso_ms'] = wind_speed.tolist()
    forecast_dict['wind_direction_iso_dgr'] = wind_direction.tolist()
    return forecast_dict

def calculate_wind_speed_and_direction(u_wind, v_wind):
    """
    Calculate wind speed and direction from u and v components.
    
    Args:
        u_wind (np.array): U component of wind (positive from west to east)
        v_wind (np.array): V component of wind (positive from south to north)
    
    Returns:
        tuple: (wind_speed, wind_direction)
            wind_speed (np.array): Wind speed in m/s
            wind_direction (np.array): Wind direction in degrees (0 at north, clockwise)
    """
    u_wind = np.asarray(u_wind, dtype=float)
    v_wind = np.asarray(v_wind, dtype=float)
    wind_speed = np.sqrt(u_wind**2 + v_wind**2)
    wind_direction = np.mod(270 - np.degrees(np.arctan2(v_wind, u_wind)), 360)
    
    return wind_speed, wind_direction

def calculate_dewpoint(temp_c, rh_percent):
    temp_c = np.asarray(temp_c, dtype=float)
    rh_percent = np.asarray(rh_percent, dtype=float)
    a, b = 17.27, 237.7
    alpha = (a * temp_c) / (b + temp_c) + np.log(rh_percent / 100.0)
    dewpoint = (b * alpha) / (a - alpha)
    return dewpoint
