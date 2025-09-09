import csv
import os
import logging

from sqlalchemy.orm import Session

from .. import crud, schemas, models

logger = logging.getLogger(__name__)

def load_spots_from_csv(db: Session, file_path: str = "app/data/spots.csv"):
    # Delete all existing spots first
    logger.info("Deleting all existing spots")
    db.query(models.Spot).delete()
    db.commit()
    
    logger.info(f"Loading spots from {file_path}")
    with open(file_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            spot = schemas.SpotCreate(
                spot_id=int(row['spot_id']),
                name=row['name'],
                latitude=float(row['latitude']),
                longitude=float(row['longitude']),
                altitude=int(row['altitude']),
                type=row['type'],
                wind_direction=row['wind_direction'] if row['wind_direction'] else None,
                site_id=int(row['site_id'])
            )
            crud.create_spot_sync(db, spot)
    
    db.commit()
    logger.info("Spots loaded successfully")