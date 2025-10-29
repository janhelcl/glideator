from typing import Any

import pandas as pd

import gfs


def load_data(engine: Any, site_col: str = "site_id", date_col: str = "date", label_col: str = "max_points") -> pd.DataFrame:
    """
    Load features and target from the database using the provided SQLAlchemy engine.

    Returns a DataFrame with columns:
    - site_col, date_col, label_col
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
            {site_col},
            {date_col},
            {label_col},
            {', '.join(col_names_full)}
        FROM glideator_fs.features_with_target
        WHERE date >= '2021-01-01'
        """,
        engine,
        parse_dates=[date_col],
    )

    return df.dropna()


