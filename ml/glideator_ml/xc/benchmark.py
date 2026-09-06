from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .preprocessing import DATE_FEATURES, TARGET_NAMES, WEATHER_TIMES


DEFAULT_SITE_FEATURES = ("latitude", "longitude", "altitude")

# Exact order returned by legacy gfs.fetch.get_col_order() and consumed by the
# currently served XC model. Database column order is not a model contract.
PRODUCTION_WEATHER_FEATURES = (
    "u_wind_500hpa_ms",
    "u_wind_550hpa_ms",
    "u_wind_600hpa_ms",
    "u_wind_650hpa_ms",
    "u_wind_700hpa_ms",
    "u_wind_750hpa_ms",
    "u_wind_800hpa_ms",
    "u_wind_850hpa_ms",
    "u_wind_900hpa_ms",
    "u_wind_925hpa_ms",
    "u_wind_950hpa_ms",
    "u_wind_975hpa_ms",
    "u_wind_1000hpa_ms",
    "v_wind_500hpa_ms",
    "v_wind_550hpa_ms",
    "v_wind_600hpa_ms",
    "v_wind_650hpa_ms",
    "v_wind_700hpa_ms",
    "v_wind_750hpa_ms",
    "v_wind_800hpa_ms",
    "v_wind_850hpa_ms",
    "v_wind_900hpa_ms",
    "v_wind_925hpa_ms",
    "v_wind_950hpa_ms",
    "v_wind_975hpa_ms",
    "v_wind_1000hpa_ms",
    "u_wind_10m_ms",
    "u_wind_100m_ms",
    "v_wind_10m_ms",
    "v_wind_100m_ms",
    "wind_gust_sfc_ms",
    "temperature_500hpa_k",
    "temperature_550hpa_k",
    "temperature_600hpa_k",
    "temperature_650hpa_k",
    "temperature_700hpa_k",
    "temperature_750hpa_k",
    "temperature_800hpa_k",
    "temperature_850hpa_k",
    "temperature_900hpa_k",
    "temperature_925hpa_k",
    "temperature_950hpa_k",
    "temperature_975hpa_k",
    "temperature_1000hpa_k",
    "temperature_2m_k",
    "temperature_80m_k",
    "temperature_100m_k",
    "dewpoint_2m_k",
    "pressure_sfc_pa",
    "precipitable_water_clm_kg_m2",
    "relative_humidity_500hpa_pct",
    "relative_humidity_550hpa_pct",
    "relative_humidity_600hpa_pct",
    "relative_humidity_650hpa_pct",
    "relative_humidity_700hpa_pct",
    "relative_humidity_750hpa_pct",
    "relative_humidity_800hpa_pct",
    "relative_humidity_850hpa_pct",
    "relative_humidity_900hpa_pct",
    "relative_humidity_925hpa_pct",
    "relative_humidity_950hpa_pct",
    "relative_humidity_975hpa_pct",
    "relative_humidity_1000hpa_pct",
    "geopotential_height_500hpa_m",
    "geopotential_height_550hpa_m",
    "geopotential_height_600hpa_m",
    "geopotential_height_650hpa_m",
    "geopotential_height_700hpa_m",
    "geopotential_height_750hpa_m",
    "geopotential_height_800hpa_m",
    "geopotential_height_850hpa_m",
    "geopotential_height_900hpa_m",
    "geopotential_height_925hpa_m",
    "geopotential_height_950hpa_m",
    "geopotential_height_975hpa_m",
    "geopotential_height_1000hpa_m",
    "geopotential_height_sfc_m",
)


@dataclass(frozen=True)
class XCFeatureContract:
    weather_features: tuple[str, ...]
    site_features: tuple[str, ...] = DEFAULT_SITE_FEATURES
    date_features: tuple[str, ...] = DATE_FEATURES
    target_names: tuple[str, ...] = TARGET_NAMES

    def weather_columns(self, hour: int) -> tuple[str, ...]:
        if hour not in WEATHER_TIMES:
            raise ValueError(f"Unsupported XC weather hour: {hour}")
        return tuple(f"{feature}_{hour}" for feature in self.weather_features)

    def as_dict(self) -> dict[str, list[str]]:
        return {
            "weather_features": list(self.weather_features),
            "site_features": list(self.site_features),
            "date_features": list(self.date_features),
            "target_names": list(self.target_names),
        }


@dataclass(frozen=True)
class XCSplit:
    train: pd.DataFrame
    evaluation: pd.DataFrame


def as_date(value: Any, *, name: str) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if pd.isna(timestamp):
        raise ValueError(f"Invalid {name}: {value!r}")
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_localize(None)
    return timestamp.normalize()


def discover_weather_features(columns: list[str]) -> tuple[str, ...]:
    """Discover a feature order for synthetic/ad-hoc CSV experiments only."""
    features = tuple(column[:-3] for column in columns if column.endswith("_12"))
    if not features:
        raise ValueError("Could not discover XC weather features ending in '_12'")
    column_set = set(columns)
    missing = [
        f"{feature}_{hour}"
        for feature in features
        for hour in WEATHER_TIMES
        if f"{feature}_{hour}" not in column_set
    ]
    if missing:
        raise ValueError(
            "Incomplete XC weather time slices; missing: " + ", ".join(missing[:8])
        )
    return features


def split_temporal(
    frame: pd.DataFrame,
    *,
    train_end: Any,
    eval_start: Any,
    eval_end: Any,
    require_known_eval_sites: bool = True,
    require_eval_boundary_coverage: bool = False,
) -> XCSplit:
    train_end_at = as_date(train_end, name="data.train_end")
    eval_start_at = as_date(eval_start, name="data.eval_start")
    eval_end_at = as_date(eval_end, name="data.eval_end")
    if eval_start_at <= train_end_at:
        raise ValueError("XC temporal evaluation must start after the training window")
    if eval_end_at < eval_start_at:
        raise ValueError("XC eval_end must be on or after eval_start")

    train = frame.loc[frame["date"] <= train_end_at].reset_index(drop=True)
    evaluation = frame.loc[
        (frame["date"] >= eval_start_at) & (frame["date"] <= eval_end_at)
    ].reset_index(drop=True)
    if train.empty or evaluation.empty:
        raise ValueError("XC temporal split requires non-empty train and evaluation sets")

    if require_eval_boundary_coverage:
        actual_start = pd.Timestamp(evaluation["date"].min()).normalize()
        actual_end = pd.Timestamp(evaluation["date"].max()).normalize()
        if actual_start != eval_start_at or actual_end != eval_end_at:
            raise ValueError(
                "XC evaluation does not cover configured boundaries: "
                f"expected {eval_start_at.date()}..{eval_end_at.date()}, "
                f"got {actual_start.date()}..{actual_end.date()}"
            )

    if require_known_eval_sites:
        unseen = sorted(set(evaluation["site_id"]) - set(train["site_id"]))
        if unseen:
            raise ValueError(
                "XC evaluation contains sites with no training history: "
                + ", ".join(str(site_id) for site_id in unseen[:12])
            )
    return XCSplit(train=train, evaluation=evaluation)


def frame_fingerprint(frame: pd.DataFrame, features: XCFeatureContract) -> str:
    columns = [
        "site_id",
        "date",
        "max_points",
        *features.site_features,
        *(column for hour in WEATHER_TIMES for column in features.weather_columns(hour)),
    ]
    canonical = frame.sort_values(["date", "site_id"], kind="mergesort").reset_index(drop=True)
    hashed = pd.util.hash_pandas_object(canonical[columns], index=False).values
    hasher = hashlib.sha256()
    hasher.update(
        json.dumps(
            {"columns": columns, "feature_contract": features.as_dict()},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    hasher.update(hashed.tobytes())
    return f"sha256:{hasher.hexdigest()}"
