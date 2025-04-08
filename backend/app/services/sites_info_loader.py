import json
import os
import logging
from sqlalchemy.orm import Session
from .. import crud, schemas, models

logger = logging.getLogger(__name__)

def load_sites_info_from_jsonl(db: Session):
    # Delete all existing site info first
    logger.info("Deleting all existing site info")
    db.query(models.SiteInfo).delete()
    db.commit()
    
    jsonl_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'sites_info.jsonl')
    logger.info(f"Loading sites info from {jsonl_path}")
    
    with open(jsonl_path, mode='r', encoding='utf-8') as file:
        for line in file:
            data = json.loads(line)
            # Convert the data to match our schema
            site_info_data = {
                "site_id": data["site_id"],
                "site_name": data["site_name"],
                "country": data["country"],
                "html": data["html"],
                "search_recs": data["search_recs"]
            }
            site_info = schemas.SiteInfoCreate(**site_info_data)
            crud.create_site_info(db, site_info)
    
    db.commit()
    logger.info("Sites info loaded successfully") 