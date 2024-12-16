import csv
import os
import logging

from sqlalchemy.orm import Session

from .. import crud, schemas


logger = logging.getLogger(__name__)


def load_sites_from_csv(db: Session, csv_filename: str):
    csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', csv_filename)
    with open(csv_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            site = schemas.SiteCreate(
                site_id=int(row['site_id']),
                name=row['name'],
                latitude=float(row['latitude']),
                longitude=float(row['longitude']),
                altitude=int(row['altitude']),
                lat_gfs=float(row['lat_gfs']),
                lon_gfs=float(row['lon_gfs'])
            )
            # Check if site already exists to prevent duplicates
            existing_site = crud.get_site(db, site.site_id)
            if not existing_site:
                crud.create_site(db, site)
    db.commit()
