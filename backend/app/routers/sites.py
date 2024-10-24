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

@router.get("/{site_name}/predictions", response_model=List[schemas.Prediction])
def read_predictions(
    site_name: str,
    query_date: Optional[date] = Query(None, description="Date to filter predictions"),
    metric: Optional[str] = Query(None, description="Metric to filter predictions"),
    db: Session = Depends(get_db)
):
    predictions = crud.get_predictions(db, site_name, query_date, metric)
    if not predictions:
        raise HTTPException(status_code=404, detail="Predictions not found")
    return predictions