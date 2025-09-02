import csv
import os
import logging

from sqlalchemy.orm import Session

from .. import crud, schemas, models

logger = logging.getLogger(__name__)

def load_flight_stats_from_csv(db: Session, file_path: str = "app/data/flight_stats.csv"):
    # Delete all existing flight stats first
    logger.info("Deleting all existing flight stats")
    db.query(models.FlightStats).delete()
    db.commit()
    
    logger.info(f"Loading flight stats from {file_path}")
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            flight_stats = schemas.FlightStatsCreate(
                site_id=int(row['site_id']),
                month=int(row['month']),
                avg_days_over_0=float(row['avg_days_over_0']),
                avg_days_over_10=float(row['avg_days_over_10']),
                avg_days_over_20=float(row['avg_days_over_20']),
                avg_days_over_30=float(row['avg_days_over_30']),
                avg_days_over_40=float(row['avg_days_over_40']),
                avg_days_over_50=float(row['avg_days_over_50']),
                avg_days_over_60=float(row['avg_days_over_60']),
                avg_days_over_70=float(row['avg_days_over_70']),
                avg_days_over_80=float(row['avg_days_over_80']),
                avg_days_over_90=float(row['avg_days_over_90']),
                avg_days_over_100=float(row['avg_days_over_100']),
            )
            crud.create_flight_stats_sync(db, flight_stats)
    
    db.commit()
    logger.info("Flight stats loaded successfully")