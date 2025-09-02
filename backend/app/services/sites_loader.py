import csv
import os
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from .. import crud, schemas, models


logger = logging.getLogger(__name__)


async def load_sites_from_csv(db: AsyncSession, csv_filename: str):
    # Delete dependent data first to avoid foreign key constraint violations
    logger.info("Deleting existing dependent data (FlightStats, Spot, Prediction, SiteInfo, SiteTag)")
    await db.execute(delete(models.FlightStats))
    await db.execute(delete(models.Spot))
    await db.execute(delete(models.Prediction))
    await db.execute(delete(models.SiteInfo))
    await db.execute(delete(models.SiteTag))
    # Now delete the sites themselves
    logger.info("Deleting all existing sites")
    await db.execute(delete(models.Site))
    await db.commit() # Commit deletions together
    
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
            await crud.create_site(db, site)
    
    await db.commit()
    logger.info("Sites loaded successfully")
