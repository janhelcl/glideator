import os
import logging
from datetime import datetime

import pandas as pd
from sqlalchemy.orm import Session

from .. import crud, schemas
import gfs.fetch
import gfs.utils
import net.io


logger = logging.getLogger(__name__)


def generate_and_store_predictions(db: Session, model_filename: str, preprocessor_filename: str, date, run, delta):
    model_path = os.path.join(os.path.dirname(__file__), '..', 'models', model_filename)
    preprocessor_path = os.path.join(os.path.dirname(__file__), '..', 'models', preprocessor_filename)

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
    launch_forecasts = gfs.fetch.add_gfs_forecast(sites_df, date, run, delta)
    predictions = net.io.apply_pipeline(launch_forecasts, preprocessor_path, model_path)

    computed_at = datetime.now()
    gfs_forecast_at = datetime(year=date.year, month=date.month, day=date.day, hour=run)
    
    # Save predictions to database
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
    
    db.commit()
