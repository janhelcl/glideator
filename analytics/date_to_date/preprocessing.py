from typing import List, Tuple

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from . import settings


def split_train_val(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    train = df[df[settings.DATE_COL] < pd.Timestamp(f"{settings.VAL_YEAR}-01-01")].copy()
    val = df[(df[settings.DATE_COL] >= pd.Timestamp(f"{settings.VAL_YEAR}-01-01")) &
             (df[settings.DATE_COL] < pd.Timestamp(f"{settings.VAL_YEAR + 1}-01-01"))].copy()
    return train, val


def get_feature_cols(df: pd.DataFrame) -> List[str]:
    non_feature = {settings.SITE_COL, settings.DATE_COL, settings.LABEL_COL}
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


