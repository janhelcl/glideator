import os
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from .. import crud, schemas
import gfs.fetch
import gfs.utils
import net.io


logger = logging.getLogger(__name__)


EXPECTED_COLUMNS = [
    *gfs.fetch.get_col_order(),
    'date',
    'run',
    'delta',
    'ref_time'
]
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_FILENAME = 'net.pth'
PREPROCESSOR_FILENAME = 'preprocessor.pkl'
MODEL_PATH = BASE_DIR / 'models' / MODEL_FILENAME
PREPROCESSOR_PATH = BASE_DIR / 'models' / PREPROCESSOR_FILENAME


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


def fetch_sites(db: Session):
    sites = crud.get_sites(db)
    sites_df = pd.DataFrame([
        {
            'launch': site.name,
            'latitude': site.latitude,
            'longitude': site.longitude,
            'altitude': site.altitude,
            'lat_gfs': site.lat_gfs,
            'lon_gfs': site.lon_gfs
        } for site in sites
    ])
    return sites_df


def process_forecasts(db: Session, forecasts):
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
    sites = (
        fetch_sites(db)
        .set_index(['lat_gfs', 'lon_gfs'])
    )
    full_data = joined_forecasts.join(sites)
    full_data['ref_time'] = full_data['ref_time_12']
    # score
    predictions = net.io.apply_pipeline(full_data, PREPROCESSOR_PATH, MODEL_PATH)
    # save
    computed_at = datetime.now()
    date = full_data['date_12'].iloc[0]
    run = full_data['run_12'].iloc[0]
    gfs_forecast_at = datetime(year=date.year, month=date.month, day=date.day, hour=run)
    _save_predictions(db, predictions, computed_at, gfs_forecast_at)
    db.commit()


def _save_predictions(db, predictions, computed_at, gfs_forecast_at):
    for site_name, pred_date, metric, value in predictions:
        prediction = schemas.PredictionCreate(
            site=site_name,
            date=pred_date,
            metric=metric,
            value=value,
            computed_at=computed_at,
            gfs_forecast_at=gfs_forecast_at
        )
        # Delete existing prediction if any
        existing_prediction = crud.get_predictions(db, site_name, pred_date, metric)
        if existing_prediction:
            db.delete(existing_prediction[0])
        # Create new prediction
        crud.create_prediction(db, prediction)
