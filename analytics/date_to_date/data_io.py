from typing import Any

import pandas as pd

import gfs
from . import settings


def load_data(engine: Any) -> pd.DataFrame:
    """
    Load features and target from the database using the provided SQLAlchemy engine.

    Returns a DataFrame with columns:
    - settings.SITE_COL, settings.DATE_COL, settings.LABEL_COL
    - hourly feature columns for hours 9, 12, 15 based on gfs.fetch.get_col_order()
    """
    col_names = gfs.fetch.get_col_order()

    col_names_full = []
    for hour in [9, 12, 15]:
        for col in col_names:
            col_names_full.append(f"{col}_{hour}")

    df = pd.read_sql(
        f"""
        SELECT
            {settings.SITE_COL},
            {settings.DATE_COL},
            {settings.LABEL_COL},
            {', '.join(col_names_full)}
        FROM glideator_fs.features_with_target
        WHERE date >= '2021-01-01'
        """,
        engine,
        parse_dates=[settings.DATE_COL],
    )

    return df.dropna()


