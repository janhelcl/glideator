from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd


XC_THRESHOLDS = tuple(range(0, 101, 10))
TARGET_NAMES = tuple(f"XC{threshold}" for threshold in XC_THRESHOLDS)
DATE_FEATURES = ("weekend", "year", "day_of_year_sin", "day_of_year_cos")
WEATHER_TIMES = (9, 12, 15)


def add_targets(
    frame: pd.DataFrame,
    max_points_col: str = "max_points",
    thresholds: Sequence[int] = XC_THRESHOLDS,
) -> pd.DataFrame:
    """Add the production XC threshold targets without mutating the input frame.

    The legacy production contract is strict: ``XCk == 1`` iff ``max_points > k``.
    """

    result = frame.copy()
    for threshold in thresholds:
        result[f"XC{threshold}"] = (result[max_points_col] > threshold).astype(int)
    return result


def add_date_features(
    frame: pd.DataFrame,
    date_col: str = "date",
) -> pd.DataFrame:
    """Add the four date features consumed by the production XC model."""

    result = frame.copy()
    dates = pd.to_datetime(result[date_col])
    result["weekend"] = (dates.dt.weekday >= 5).astype(int)
    result["year"] = dates.dt.year
    day_of_year = dates.dt.dayofyear
    result["day_of_year_sin"] = np.sin(2 * np.pi * day_of_year / 365.25)
    result["day_of_year_cos"] = np.cos(2 * np.pi * day_of_year / 365.25)
    return result


def weather_features_by_time(
    weather_features: Sequence[str],
) -> dict[int, list[str]]:
    """Split flattened production weather columns into the 09/12/15 inputs.

    This deliberately preserves the suffix-based behavior used by ``net.io`` today.
    """

    return {
        hour: [feature for feature in weather_features if feature.endswith(str(hour))]
        for hour in WEATHER_TIMES
    }
