import csv
import os
import logging

from sqlalchemy.orm import Session

from .. import crud, schemas, models


logger = logging.getLogger(__name__)


def load_sites_from_csv(db: Session, csv_filename: str):
    # Delete dependent data first to avoid foreign key constraint violations
    logger.info("Deleting existing dependent data (FlightStats, Spot, Prediction, SiteInfo, SiteTag)")
    db.query(models.FlightStats).delete()
    db.query(models.Spot).delete()
    db.query(models.Prediction).delete()
    db.query(models.SiteInfo).delete()
    db.query(models.SiteTag).delete()
    # Now delete the sites themselves
    logger.info("Deleting all existing sites")
    db.query(models.Site).delete()
    db.commit() # Commit deletions together
    
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', csv_filename)
    logger.info(f"Loading sites from {csv_path}")
    
    with open(csv_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            site = schemas.SiteBase(
                site_id=int(row['site_id']),
                name=row['name'],
                latitude=float(row['latitude']),
                longitude=float(row['longitude']),
                altitude=int(row['altitude']),
                lat_gfs=float(row['lat_gfs']),
                lon_gfs=float(row['lon_gfs'])
            )
            crud.create_site_sync(db, site)
    
    db.commit()
    logger.info("Sites loaded successfully")
