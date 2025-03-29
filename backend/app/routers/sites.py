import json
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from datetime import date

from .. import schemas, crud
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

@router.get("/{site_id}/flight_stats", response_model=Dict[int, List[float]])
def get_flight_stats(site_id: int, db: Session = Depends(get_db)):
    """
    Get flight stats data for a specific site organized by temperature thresholds
    """
    flight_stats = crud.get_flight_stats_by_site_id(db, site_id)
    
    if not flight_stats:
        raise HTTPException(status_code=404, detail=f"Flight stats not found for site {site_id}")
    
    # Initialize the result dictionary with empty lists for each temperature threshold
    result = {
        0: [], 10: [], 20: [], 30: [], 40: [], 
        50: [], 60: [], 70: [], 80: [], 90: [], 100: []
    }
    
    # Populate the result dictionary
    for stat in flight_stats:
        result[0].append(stat.avg_days_over_0)
        result[10].append(stat.avg_days_over_10)
        result[20].append(stat.avg_days_over_20)
        result[30].append(stat.avg_days_over_30)
        result[40].append(stat.avg_days_over_40)
        result[50].append(stat.avg_days_over_50)
        result[60].append(stat.avg_days_over_60)
        result[70].append(stat.avg_days_over_70)
        result[80].append(stat.avg_days_over_80)
        result[90].append(stat.avg_days_over_90)
        result[100].append(stat.avg_days_over_100)
    
    return result

@router.get("/{site_id}/spots", response_model=List[schemas.Spot], summary="Get Spots for Site")
def get_spots_for_site(site_id: int, db: Session = Depends(get_db)):
    """
    Get all takeoff and landing spots for a specific site
    """
    # Check if site exists
    site = crud.get_site(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site with ID {site_id} not found")
    
    # Get all spots for the site
    spots = crud.get_spots_by_site_id(db, site_id)
    
    # If no spots found, return empty list (not 404)
    return spots

@router.get("/{site_id}/info", response_model=schemas.SiteInfo, summary="Get Site Info")
def get_site_info(site_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific site including description, facilities, access, etc.
    """
    # Check if site exists
    site = crud.get_site(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site with ID {site_id} not found")
    
    # Get site info
    site_info = crud.get_site_info(db, site_id)
    if not site_info:
        raise HTTPException(status_code=404, detail=f"Site info not found for site {site_id}")
    
    return site_info