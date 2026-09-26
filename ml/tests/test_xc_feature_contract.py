from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from glideator_ml.xc.benchmark import PRODUCTION_WEATHER_FEATURES
from glideator_ml.xc.data import prepare_xc_data


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_production_weather_order_matches_legacy_gfs_schema() -> None:
    schema = json.loads(
        (_repo_root() / "gfs" / "gfs" / "schema.json").read_text(encoding="utf-8")
    )
    legacy_order = tuple(
        name for name, _ in sorted(schema.items(), key=lambda item: item[1]["position"])
    )

    assert len(PRODUCTION_WEATHER_FEATURES) == 77
    assert PRODUCTION_WEATHER_FEATURES == legacy_order


def test_database_data_uses_production_order_not_column_order() -> None:
    row = {
        "site_id": 1,
        "date": "2024-01-01",
        "max_points": 25.0,
        "latitude": 50.0,
        "longitude": 14.0,
        "altitude": 400.0,
    }
    for hour in (15, 12, 9):
        for index, feature in enumerate(reversed(PRODUCTION_WEATHER_FEATURES)):
            row[f"{feature}_{hour}"] = float(index + hour)
    raw = pd.DataFrame([row])

    _, features = prepare_xc_data(raw, {"source": "database"})

    assert features.weather_features == PRODUCTION_WEATHER_FEATURES
