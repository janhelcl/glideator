from __future__ import annotations

import os
import re
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text

from .benchmark import (
    DEFAULT_SITE_FEATURES,
    PRODUCTION_WEATHER_FEATURES,
    XCFeatureContract,
    as_date,
    discover_weather_features,
)
from .preprocessing import WEATHER_TIMES, add_date_features, add_targets


_TABLE_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*")


def _feature_contract(raw: pd.DataFrame, config: dict[str, Any]) -> XCFeatureContract:
    configured_weather = config.get("weather_features")
    if configured_weather:
        weather = tuple(str(value) for value in configured_weather)
    elif str(config.get("source", "database")) == "database":
        # Production training and serving use gfs.fetch.get_col_order(). Keep that
        # order explicit here instead of depending on SELECT * / DataFrame order.
        weather = PRODUCTION_WEATHER_FEATURES
    else:
        weather = discover_weather_features(list(raw.columns))
    site = tuple(str(value) for value in config.get("site_features", DEFAULT_SITE_FEATURES))
    return XCFeatureContract(weather_features=weather, site_features=site)


def prepare_xc_data(raw: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, XCFeatureContract]:
    required_base = {"site_id", "date", "max_points"}
    missing_base = required_base - set(raw.columns)
    if missing_base:
        raise ValueError(f"Missing XC input columns: {', '.join(sorted(missing_base))}")

    features = _feature_contract(raw, config)
    required = set(required_base) | set(features.site_features)
    for hour in WEATHER_TIMES:
        required.update(features.weather_columns(hour))
    missing = required - set(raw.columns)
    if missing:
        raise ValueError("Missing XC feature columns: " + ", ".join(sorted(missing)[:12]))

    frame = raw.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    if config.get("start_date") is not None:
        frame = frame.loc[frame["date"] >= as_date(config["start_date"], name="data.start_date")]
    end_date = config.get("end_date", config.get("eval_end"))
    if end_date is not None:
        frame = frame.loc[frame["date"] <= as_date(end_date, name="data.end_date")]

    numeric = [
        "site_id",
        "max_points",
        *features.site_features,
        *(column for hour in WEATHER_TIMES for column in features.weather_columns(hour)),
    ]
    for column in numeric:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if config.get("max_site_id") is not None:
        frame = frame.loc[frame["site_id"] <= int(config["max_site_id"])]
    frame = frame.dropna(subset=["date", *numeric]).copy()
    if frame.empty:
        raise ValueError("XC data preparation produced an empty dataset")
    if (frame["max_points"] < 0).any():
        raise ValueError("XC max_points must be non-negative")

    frame["site_id"] = frame["site_id"].astype(int)
    duplicates = frame.duplicated(["site_id", "date"], keep=False)
    if duplicates.any():
        raise ValueError("XC dataset must contain exactly one row per site/date")

    frame = add_targets(frame, max_points_col="max_points")
    frame = add_date_features(frame, date_col="date")
    frame = frame.sort_values(["date", "site_id"], kind="mergesort").reset_index(drop=True)
    return frame, features


def load_xc_data(config: dict[str, Any]) -> tuple[pd.DataFrame, XCFeatureContract]:
    source = str(config.get("source", "database"))
    if source == "csv":
        path = config.get("path")
        if not path:
            raise ValueError("data.path is required when data.source=csv")
        return prepare_xc_data(pd.read_csv(path), config)
    if source != "database":
        raise ValueError(f"Unsupported XC data source: {source!r}")

    env_name = str(config.get("database_url_env", "ML_DATABASE_URL"))
    database_url = os.getenv(env_name)
    if not database_url:
        raise RuntimeError(f"Environment variable {env_name!r} is not set")
    table = str(config.get("table", "glideator_fs.features_with_target"))
    if not _TABLE_RE.fullmatch(table):
        raise ValueError(f"Invalid XC source table: {table!r}")

    start = config.get("start_date")
    end = config.get("end_date", config.get("eval_end"))
    if start is None or end is None:
        raise ValueError("XC database extraction requires data.start_date and data.eval_end")
    params: dict[str, Any] = {
        "start": str(as_date(start, name="data.start_date").date()),
        "end": str(as_date(end, name="data.eval_end").date()),
    }
    clauses = ["date >= :start", "date <= :end"]
    if config.get("max_site_id") is not None:
        clauses.append("site_id <= :max_site_id")
        params["max_site_id"] = int(config["max_site_id"])
    query = text(f"select * from {table} where {' and '.join(clauses)} order by date, site_id")

    engine = create_engine(database_url)
    with engine.connect() as connection:
        raw = pd.read_sql(query, connection, params=params, parse_dates=["date"])
    return prepare_xc_data(raw, config)


def fit_scaling_params(
    train: pd.DataFrame,
    features: XCFeatureContract,
) -> tuple[dict[str, dict[str, float]], dict[str, dict[str, float]]]:
    """Fit legacy scaler statistics; weather uses noon rows exactly as before."""

    def stats(column: str) -> dict[str, float]:
        mean = float(train[column].mean())
        std = float(train[column].std(ddof=1))
        if not pd.notna(mean) or not pd.notna(std) or std <= 0:
            raise ValueError(f"Cannot fit XC scaler for {column!r}: mean={mean}, std={std}")
        return {"mean": mean, "std": std}

    weather = {f"{name}_12": stats(f"{name}_12") for name in features.weather_features}
    site = {name: stats(name) for name in features.site_features}
    return weather, site
