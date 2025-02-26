import json
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date

from .. import models, schemas, crud
from ..database import SessionLocal

router = APIRouter(
    prefix="/sites",
    tags=["sites"],
    responses={404: {"description": "Not found"}},
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/", response_model=schemas.Site)
def create_site(site: schemas.SiteCreate, db: Session = Depends(get_db)):
    db_site = crud.create_site(db, site)
    return db_site

@router.get("/", response_model=List[schemas.SiteResponse])
def read_sites(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    sites = crud.get_sites_with_predictions(db, skip=skip, limit=limit)
    return sites

@router.get("/{site_id}/predictions", response_model=List[schemas.SiteResponse])
def read_predictions(
    site_id: int,
    db: Session = Depends(get_db),
    date: Optional[date] = None,
    metric: Optional[str] = None
):
    site = crud.get_site(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    predictions = crud.get_predictions(db, site_id, date, metric)
    
    # Group predictions by date
    predictions_by_date = defaultdict(lambda: {'metrics': {}, 'computed_at': None, 'gfs_forecast_at': None})
    for pred in predictions:
        predictions_by_date[pred.date]['metrics'][pred.metric] = pred.value
        predictions_by_date[pred.date]['computed_at'] = pred.computed_at
        predictions_by_date[pred.date]['gfs_forecast_at'] = pred.gfs_forecast_at
    
    # Format predictions in the same way as the /sites/ endpoint
    predictions_list = []
    for date, data in sorted(predictions_by_date.items()):
        metrics_dict = data['metrics']
        ordered_values = [
            metrics_dict.get(f'XC{i}', 0.0)
            for i in [0] + list(range(10, 101, 10))
        ]
        predictions_list.append(
            schemas.PredictionValues(
                date=date,
                values=ordered_values,
                computed_at=data['computed_at'],
                gfs_forecast_at=data['gfs_forecast_at']
            )
        )
    
    # Create a single SiteResponse object with all predictions
    site_response = schemas.SiteResponse(
        name=site.name,
        latitude=site.latitude,
        longitude=site.longitude,
        site_id=site.site_id,
        predictions=predictions_list
    )
    
    return [site_response]  # Return as a list to match the expected response_model

@router.get("/{site_id}/forecast", response_model=schemas.Forecast)
def read_forecast(
    site_id: int,
    query_date: date = Query(..., description="Date of the forecast"),
    db: Session = Depends(get_db)
):
    site = crud.get_site(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    forecast = crud.get_forecast(db, query_date, site.lat_gfs, site.lon_gfs)
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast not found")
    
    # Ensure that the JSON fields are properly serialized
    forecast.forecast_9 = json.dumps(forecast.forecast_9)
    forecast.forecast_12 = json.dumps(forecast.forecast_12)
    forecast.forecast_15 = json.dumps(forecast.forecast_15)
    
    return forecast
