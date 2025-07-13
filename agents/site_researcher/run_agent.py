import os
import json
import logging
import argparse
from typing import Any, Dict

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from pydantic import BaseModel

from src.agents import site_researcher_graph


def serialize(obj: Any) -> Any:
    """Recursively convert Pydantic objects to plain Python types so they can
    be serialised by ``json.dumps``.
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if isinstance(obj, list):
        return [serialize(i) for i in obj]
    if isinstance(obj, dict):
        return {k: serialize(v) for k, v in obj.items()}
    return obj


def get_sites(engine):
    """Return a DataFrame with *all* paragliding sites available in the mart.

    Adjust the SQL query if you need to filter the list (e.g. by country).
    """
    query = """
    SELECT
        site_id,
        name,
        country
    FROM glideator_mart.dim_sites
    ORDER BY site_id
    """
    return pd.read_sql(query, engine)


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Run the Site Researcher agent for all sites and store the results as JSON Lines."
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        default=os.getenv("SITE_RESEARCHER_OUTPUT", "sites_info_extended.jsonl"),
        help="Path to output JSONL file (default: %(default)s)"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    connection_string = (
        "postgresql://{user}:{password}@{host}:{port}/{db}".format(
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            db=os.getenv("DB_NAME"),
        )
    )
    engine = create_engine(connection_string)

    output_path = args.output_path

    sites = get_sites(engine)
    logging.info("Processing %s sites", len(sites))

    for site in sites.itertuples():
        logging.info("Processing site: %s (%s)", site.name, site.country)
        try:
            site_info = site_researcher_graph.invoke({"site_name": site.name})

            record = {
                "site_id": site.site_id,
                "site_name": site.name,
                "country": site.country,
            }
            filtered_info = {
                k: v
                for k, v in serialize(site_info).items()
                if k not in {"risk_report", "overview_report", "access_report", "full_report"}
            }
            record.update(filtered_info)

            with open(output_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
            logging.info("✔ Finished site: %s (%s)", site.name, site.country)
        except Exception as exc:
            logging.exception("✖ Error processing %s (%s): %s", site.name, site.country, exc)


if __name__ == "__main__":
    main()