from typing import Any, Iterable, List

import pandas as pd
import numpy as np
import pickle
from pathlib import Path

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


def export_scaled_features_jsonl(
    df: pd.DataFrame,
    feat_cols: List[str],
    output_path: str | Path,
    site_col: str = "site_id",
    date_col: str = "date",
) -> None:
    """
    Export a JSONL where each line contains {site_id, date, features} and
    features is a list[float] of the SCALED feature vector in the order of feat_cols.

    Assumes the provided DataFrame already contains SCALED values in feat_cols.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure correct ordering and types
    cols = [site_col, date_col] + list(feat_cols)
    df_exp = df.loc[:, cols].copy()

    # Normalize date to ISO string to make JSONL portable
    if np.issubdtype(df_exp[date_col].dtype, np.datetime64):
        df_exp[date_col] = df_exp[date_col].dt.strftime("%Y-%m-%d")

    with path.open("w", encoding="utf-8") as f:
        for _, row in df_exp.iterrows():
            record = {
                "site_id": row[site_col],
                "date": row[date_col],
                "features": [
                    float(row[c]) if pd.notna(row[c]) else None for c in feat_cols
                ],
            }
            # Manual, fast JSON line without importing json for speed/consistency
            # but keep it robust via pandas/numpy casting above
            import json  # local import to avoid global cost if unused
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def save_scaler_pickle(scaler: Any, output_path: str | Path) -> None:
    """
    Persist the fitted scaler object using pickle.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(scaler, f, protocol=pickle.HIGHEST_PROTOCOL)

