from sqlalchemy.orm import Session, selectinload, with_loader_criteria
from sqlalchemy import and_, func
from collections import defaultdict
from . import models, schemas
from typing import Optional, List
from datetime import date, datetime

def get_site(db: Session, site_id: int):
    return db.query(models.Site).filter(models.Site.site_id == site_id).first()

def get_site_by_name(db: Session, name: str):
    return db.query(models.Site).filter(models.Site.name == name).first()

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

def get_site_list(db: Session):
    """
    Retrieves a list of all sites with their IDs and names.
    """
    return db.query(models.Site.site_id, models.Site.name).all()

def get_tags_by_site_id(db: Session, site_id: int) -> List[str]:
    return [row.tag for row in db.query(models.SiteTag).filter(models.SiteTag.site_id == site_id).all()]

def replace_site_tags(db: Session, site_id: int, tags: List[str]):
    db.query(models.SiteTag).filter(models.SiteTag.site_id == site_id).delete()
    for t in tags:
        db_tag = models.SiteTag(site_id=site_id, tag=t)
        db.add(db_tag)
    db.commit()

def get_all_unique_tags(db: Session) -> List[str]:
    """Return all unique tag strings across sites."""
    return [row[0] for row in db.query(models.SiteTag.tag).distinct().order_by(models.SiteTag.tag.asc()).all()]

def get_tags_with_min_sites(db: Session, min_sites: int = 2) -> List[str]:
    """Return tags that are used by at least min_sites distinct sites."""
    q = (
        db.query(models.SiteTag.tag)
        .group_by(models.SiteTag.tag)
        .having(func.count(func.distinct(models.SiteTag.site_id)) >= min_sites)
        .order_by(models.SiteTag.tag.asc())
    )
    return [row[0] for row in q.all()]

def get_predictions(db: Session, site_id: int, query_date: Optional[date] = None, metric: Optional[str] = None):
    """
    Retrieves predictions based on site_id, and optionally filters by date and metric.
    """
    query = db.query(models.Prediction).filter(models.Prediction.site_id == site_id)
    
    if query_date:
        query = query.filter(models.Prediction.date == query_date)
    
    if metric:
        query = query.filter(models.Prediction.metric == metric)
    
    return query.all()

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

def create_forecast(db: Session, forecast: schemas.ForecastCreate):
    db_forecast = models.Forecast(**forecast.dict())
    db.add(db_forecast)
    db.commit()
    db.refresh(db_forecast)
    return db_forecast

def get_forecasts_by_date(db: Session, query_date: date) -> List[models.Forecast]:
    return db.query(models.Forecast).filter(models.Forecast.date == query_date).all()

def get_forecast(db: Session, query_date: date, lat_gfs: float, lon_gfs: float) -> Optional[models.Forecast]:
    return db.query(models.Forecast).filter(
        models.Forecast.date == query_date,
        models.Forecast.lat_gfs == lat_gfs,
        models.Forecast.lon_gfs == lon_gfs
    ).first()

def delete_forecasts_by_date(db: Session, query_date: date):
    db.query(models.Forecast).filter(models.Forecast.date == query_date).delete()
    db.commit()

def get_sites_with_predictions(db: Session, skip: int = 0, limit: int = 100):
    sites = db.query(models.Site).offset(skip).limit(limit).all()
    site_predictions = defaultdict(lambda: defaultdict(dict))  # Changed to dict instead of list

    predictions = (
        db.query(models.Prediction)
        .filter(models.Prediction.site_id.in_([site.site_id for site in sites]))
        .order_by(models.Prediction.date, models.Prediction.metric)
        .all()
    )

    # Store predictions by site_id and date
    for pred in predictions:
        if pred.date not in site_predictions[pred.site_id]:
            site_predictions[pred.site_id][pred.date] = {
                'metrics': {},
                'computed_at': pred.computed_at,
                'gfs_forecast_at': pred.gfs_forecast_at
            }
        site_predictions[pred.site_id][pred.date]['metrics'][pred.metric] = pred.value

    result = []
    for site in sites:
        predictions_list = []
        for pred_date in sorted(site_predictions[site.site_id].keys()):
            pred_data = site_predictions[site.site_id][pred_date]
            metrics_dict = pred_data['metrics']
            # Ensure consistent ordering: XC0, XC10, XC20, ..., XC100
            ordered_values = [
                metrics_dict.get(f'XC{i}', 0.0)
                for i in [0] + list(range(10, 101, 10))
            ]
            predictions_list.append(schemas.PredictionValues(
                date=pred_date,
                values=ordered_values,
                computed_at=pred_data['computed_at'],
                gfs_forecast_at=pred_data['gfs_forecast_at']
            ))
        
        site_response = schemas.SiteResponse(
            name=site.name,
            latitude=site.latitude,
            longitude=site.longitude,
            site_id=site.site_id,
            predictions=predictions_list,
            tags=get_tags_by_site_id(db, site.site_id)
        )
        result.append(site_response)

    return result

def get_flight_stats(db: Session, site_id: int, month: int):
    return db.query(models.FlightStats).filter(
        models.FlightStats.site_id == site_id,
        models.FlightStats.month == month
    ).first()

def create_flight_stats(db: Session, flight_stats: schemas.FlightStatsCreate):
    db_flight_stats = models.FlightStats(**flight_stats.dict())
    db.add(db_flight_stats)
    db.commit()
    db.refresh(db_flight_stats)
    return db_flight_stats

def get_flight_stats_by_site_id(db: Session, site_id: int):
    return db.query(models.FlightStats).filter(
        models.FlightStats.site_id == site_id
    ).order_by(models.FlightStats.month).all()

def get_spot(db: Session, spot_id: int):
    return db.query(models.Spot).filter(models.Spot.spot_id == spot_id).first()

def get_spots_by_site_id(db: Session, site_id: int):
    return db.query(models.Spot).filter(models.Spot.site_id == site_id).all()

def create_spot(db: Session, spot: schemas.SpotCreate):
    db_spot = models.Spot(**spot.dict())
    db.add(db_spot)
    db.commit()
    db.refresh(db_spot)
    return db_spot

def create_site_info(db: Session, site_info: schemas.SiteInfoCreate):
    db_site_info = models.SiteInfo(**site_info.dict())
    db.add(db_site_info)
    db.commit()
    db.refresh(db_site_info)
    return db_site_info

def get_site_info(db: Session, site_id: int):
    return db.query(models.SiteInfo).filter(models.SiteInfo.site_id == site_id).first()

def create_site(db: Session, site: schemas.SiteBase):
    db_site = models.Site(**site.dict())
    db.add(db_site)
    db.commit()
    db.refresh(db_site)
    return db_site

# --- Trip Planning CRUD Functions ---

def get_predictions_for_range(
    db: Session, 
    start_date: date, 
    end_date: date, 
    metric: str = 'XC0' # Default to XC0 as per MVP spec
) -> List[models.Prediction]:
    """
    Retrieves predictions for a specific metric within a given date range for all sites.
    
    NOTE: This currently fetches predictions based on the 'metric' column.
    If the schema changes to have XC0, XC50 etc as direct columns, this needs adjustment.
    """
    return db.query(models.Prediction).filter(
        models.Prediction.date >= start_date,
        models.Prediction.date <= end_date,
        models.Prediction.metric == metric # Assuming Prediction model has 'metric' and 'value' columns
    ).all()

def get_sites_by_ids(db: Session, site_ids: List[int]) -> List[models.Site]:
    """
    Retrieves site details (specifically ID and name) for a list of site IDs.
    """
    if not site_ids:
        return []
    return db.query(models.Site).filter(
        models.Site.site_id.in_(site_ids)
    ).all()

def get_all_flight_stats(db: Session) -> List[models.FlightStats]:
    """
    Retrieves all flight statistics for all sites.
    """
    return db.query(models.FlightStats).all()
