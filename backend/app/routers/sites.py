import json

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

@router.get("/", response_model=List[schemas.Site])
def read_sites(
    skip: int = 0,
    limit: int = 100,
    metric: Optional[str] = Query(None, description="Metric to filter predictions"),
    date: Optional[date] = Query(None, description="Date to filter predictions"),
    db: Session = Depends(get_db)
):
    sites = crud.get_sites(db, skip=skip, limit=limit, metric=metric, date=date)
    return sites

@router.get("/{site_id}/predictions", response_model=List[schemas.Prediction])
def read_predictions(
    site_id: int,
    query_date: Optional[date] = Query(None, description="Date to filter predictions"),
    metric: Optional[str] = Query(None, description="Metric to filter predictions"),
    db: Session = Depends(get_db)
):
    site = crud.get_site(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
        
    predictions = crud.get_predictions(db, site_id, query_date, metric)
    if not predictions:
        raise HTTPException(status_code=404, detail="Predictions not found")
    return predictions

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
