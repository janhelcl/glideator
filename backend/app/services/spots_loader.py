import csv
import os
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete

from .. import crud, schemas, models

logger = logging.getLogger(__name__)

async def load_spots_from_csv(db: AsyncSession, file_path: str = "app/data/spots.csv"):
    # Delete all existing spots first
    logger.info("Deleting all existing spots")
    await db.execute(delete(models.Spot))
    await db.commit()
    
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
            await crud.create_spot(db, spot)
    
    await db.commit()
    logger.info("Spots loaded successfully")