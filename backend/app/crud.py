from sqlalchemy.orm import Session, selectinload, with_loader_criteria
from sqlalchemy import and_
from . import models, schemas
from typing import Optional
from datetime import date, datetime

def get_site(db: Session, site_name: str):
    return db.query(models.Site).filter(models.Site.name == site_name).first()

def get_sites(
    db: Session, 
    skip: int = 0, 
    limit: int = 100, 
    metric: Optional[str] = None, 
    date: Optional[date] = None
):
    query = db.query(models.Site)
    
    if metric and date:
        query = query.options(
            with_loader_criteria(models.Prediction, 
                                 and_(
                                     models.Prediction.metric == metric,
                                     models.Prediction.date == date
                                 ), 
                                 include_aliases=True)
        ).options(selectinload(models.Site.predictions))
        
        query = query.join(models.Site.predictions).filter(
            and_(
                models.Prediction.metric == metric,
                models.Prediction.date == date
            )
        ).distinct()
    
    sites = query.offset(skip).limit(limit).all()
    return sites

def create_site(db: Session, site: schemas.SiteCreate):
    db_site = models.Site(**site.dict())
    db.add(db_site)
    db.commit()
    db.refresh(db_site)
    return db_site

def get_predictions(db: Session, site_name: str, query_date: date, metric: str):
    return db.query(models.Prediction).filter(
        models.Prediction.site == site_name,
        models.Prediction.date == query_date,
        models.Prediction.metric == metric
    ).all()

def create_prediction(db: Session, prediction: schemas.PredictionCreate):
    db_prediction = models.Prediction(**prediction.dict())
    db.add(db_prediction)
    db.commit()
    db.refresh(db_prediction)
    return db_prediction

def get_latest_gfs_forecast(db: Session) -> Optional[datetime]:
    """
    Retrieves the latest gfs_forecast_at timestamp from predictions.
    """
    latest_prediction = db.query(models.Prediction).order_by(models.Prediction.gfs_forecast_at.desc()).first()
    return latest_prediction.gfs_forecast_at if latest_prediction else None