from datetime import datetime

import pandas as pd


def get_current_date():
    """Get current date in a readable format."""
    return datetime.now().strftime("%B %d, %Y")


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
    WHERE site_id < 251
    ORDER BY site_id
    """
    return pd.read_sql(query, engine)