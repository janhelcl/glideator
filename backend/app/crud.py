from sqlalchemy.orm import Session
from . import models, schemas
from typing import List
from datetime import date

def get_site(db: Session, site_name: str):
    return db.query(models.Site).filter(models.Site.name == site_name).first()

def get_sites(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Site).offset(skip).limit(limit).all()

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