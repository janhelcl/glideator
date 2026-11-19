from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .benchmark import as_date


@dataclass(frozen=True)
class XCDevelopmentSplit:
    fit: pd.DataFrame
    validation: pd.DataFrame


def split_development(
    frame: pd.DataFrame,
    *,
    validation_start: Any,
) -> XCDevelopmentSplit:
    """Create an internal temporal validation set before benchmark evaluation."""

    validation_start_at = as_date(validation_start, name="model.validation_start")
    fit = frame.loc[frame["date"] < validation_start_at].reset_index(drop=True)
    validation = frame.loc[frame["date"] >= validation_start_at].reset_index(drop=True)
    if fit.empty or validation.empty:
        raise ValueError(
            "XC development split requires rows on both sides of model.validation_start"
        )
    if fit["date"].max() >= validation["date"].min():
        raise ValueError("XC fit and validation windows must be temporally ordered")
    return XCDevelopmentSplit(fit=fit, validation=validation)
