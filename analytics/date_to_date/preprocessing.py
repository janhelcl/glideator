from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler


def split_train_val(df: pd.DataFrame, date_col: str = "date", val_year: int = 2024) -> Tuple[pd.DataFrame, pd.DataFrame]:
    train = df[df[date_col] < pd.Timestamp(f"{val_year}-01-01")].copy()
    val = df[(df[date_col] >= pd.Timestamp(f"{val_year}-01-01")) &
             (df[date_col] < pd.Timestamp(f"{val_year + 1}-01-01"))].copy()
    return train, val


def get_feature_cols(df: pd.DataFrame, site_col: str = "site_id", date_col: str = "date", label_col: str = "max_points") -> List[str]:
    non_feature = {site_col, date_col, label_col}
    return [
        c for c in df.columns
        if c not in non_feature and np.issubdtype(df[c].dtype, np.number)
    ]


def fit_scaler(train_df: pd.DataFrame, feat_cols: List[str]) -> StandardScaler:
    scaler = StandardScaler(with_mean=True, with_std=True)
    scaler.fit(train_df[feat_cols].values)
    return scaler


def bin_column(series: pd.Series) -> pd.Series:
    """
    Bin a pandas Series according to:
    - 0 stays 0
    - (0,10] -> 10, (10,20] -> 20, ... (90,100] -> 100
    - (100,inf) -> 110
    """

    def bin_value(x):
        if x == 0:
            return 0
        elif x > 0 and x <= 100:
            return int(np.ceil(x / 10) * 10)
        elif x > 100:
            return 110
        return x  # fallback, shouldn't be hit

    return series.apply(bin_value)


