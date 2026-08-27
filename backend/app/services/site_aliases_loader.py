import csv
import logging
import os

from sqlalchemy.orm import Session

from .. import models
from .site_search import normalize_site_search_text


logger = logging.getLogger(__name__)


def load_site_aliases_from_csv(
    db: Session,
    csv_filename: str = "site_aliases.csv",
) -> None:
    """Replace curated site aliases from the bundled seed file."""
    db.query(models.SiteAlias).delete()
    db.commit()

    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", csv_filename)
    loaded = 0

    with open(csv_path, mode="r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            alias = row["alias"].strip()
            if not alias:
                continue

            db.add(
                models.SiteAlias(
                    site_id=int(row["site_id"]),
                    alias=alias,
                    alias_normalized=normalize_site_search_text(alias),
                )
            )
            loaded += 1

    db.commit()
    logger.info("Loaded %d site aliases", loaded)
