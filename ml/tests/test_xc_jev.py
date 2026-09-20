from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd

from glideator_ml.xc.benchmark import PRODUCTION_WEATHER_FEATURES
from glideator_ml.xc.data import prepare_xc_data
from glideator_ml.xc.jev import (
    JEV_MODEL_VERSION,
    JEV_PROMPT_VERSION,
    build_jev_questions,
    build_jev_state,
    fit_historical_priors,
    run_xc_jev,
)
from glideator_ml.xc.preprocessing import TARGET_NAMES, WEATHER_TIMES


HEIGHTS = {
    1000: 100,
    975: 300,
    950: 500,
    925: 700,
    900: 900,
    850: 1500,
    800: 2000,
    750: 2500,
    700: 3000,
    650: 3500,
    600: 4200,
    550: 4900,
    500: 5600,
}


def _weather_value(name: str) -> float:
    if name.startswith("u_wind"):
        return 3.0
    if name.startswith("v_wind"):
        return 2.0
    if name == "wind_gust_sfc_ms":
        return 6.0
    if name == "temperature_2m_k":
        return 291.15
    if name in {"temperature_80m_k", "temperature_100m_k"}:
        return 290.5
    if name == "dewpoint_2m_k":
        return 285.15
    if name == "pressure_sfc_pa":
        return 97_000.0
    if name == "precipitable_water_clm_kg_m2":
        return 20.0
    if name == "geopotential_height_sfc_m":
        return 300.0
    if name.startswith("relative_humidity_"):
        return 55.0
    if name.startswith("geopotential_height_"):
        level = int(name.split("_")[2].removesuffix("hpa"))
        return float(HEIGHTS[level])
    if name.startswith("temperature_"):
        level = int(name.split("_")[1].removesuffix("hpa"))
        height = HEIGHTS[level]
        return 291.15 - 0.0065 * max(0, height - 300)
    raise AssertionError(f"Unhandled weather feature {name}")


def _prepared_data() -> tuple[pd.DataFrame, object]:
    rows = []
    for date, max_points in [
        ("2021-06-01", 0),
        ("2022-06-01", 45),
        ("2023-06-01", 80),
        ("2024-01-01", 20),
        ("2024-11-30", 110),
    ]:
        row = {
            "site_id": 1,
            "date": date,
            "max_points": max_points,
            "latitude": 50.1,
            "longitude": 14.4,
            "altitude": 300.0,
        }
        for hour in WEATHER_TIMES:
            for feature in PRODUCTION_WEATHER_FEATURES:
                row[f"{feature}_{hour}"] = _weather_value(feature)
        rows.append(row)
    return prepare_xc_data(
        pd.DataFrame(rows),
        {
            "source": "csv",
            "weather_features": list(PRODUCTION_WEATHER_FEATURES),
            "start_date": "2021-01-01",
            "eval_end": "2024-11-30",
            "site_features": ["latitude", "longitude", "altitude"],
        },
    )


def _config(output_dir: str) -> dict[str, object]:
    return {
        "task": "xc",
        "data": {
            "split_strategy": "temporal",
            "train_end": "2023-12-31",
            "eval_start": "2024-01-01",
            "eval_end": "2024-11-30",
            "require_known_eval_sites": True,
            "require_eval_boundary_coverage": True,
        },
        "model": {
            "name": "xc-jev-test",
            "version": JEV_MODEL_VERSION,
            "prompt_version": JEV_PROMPT_VERSION,
            "validation_start": "2023-01-01",
            "context_policy": "fit_parity",
            "historical_prior_strength": 2.0,
            "concurrency": 2,
            "requests_per_minute": 1_000_000,
        },
        "evaluation": {"benchmark_id": "xc-temporal-2024-jan-nov-v1"},
        "artifact": {"output_dir": output_dir},
        "tracking": {"enabled": False},
    }


def test_jev_state_is_semantic_and_never_contains_the_label() -> None:
    frame, _ = _prepared_data()
    row = frame.loc[frame["date"] == pd.Timestamp("2024-01-01")].iloc[0]

    state = build_jev_state(row)
    serialized = json.dumps(state)

    assert "max_points" not in serialized
    assert all(target not in serialized for target in TARGET_NAMES)
    assert state["forecast"][0]["surface_wind"]["description"] == "light from SW"
    assert state["forecast"][0]["thermal_profile"]["description"] in {
        "stable",
        "weakly unstable",
        "strongly unstable",
    }


def test_jev_questions_use_fit_only_smoothed_history() -> None:
    frame, _ = _prepared_data()
    fit = frame.loc[frame["date"] < pd.Timestamp("2023-01-01")]
    eval_row = frame.loc[frame["date"] == pd.Timestamp("2024-11-30")].iloc[0]
    priors = fit_historical_priors(fit, smoothing_strength=2.0)

    questions = build_jev_questions(eval_row, priors)

    assert tuple(questions) == TARGET_NAMES
    assert "strictly more than 100" in questions["XC100"]["instructions"]["proposition"]
    assert questions["XC100"]["criteria"]["false"].endswith("at most 100.")
    # The 2024 row is positive at XC100, but both fit rows are not. Its label must
    # not leak into the historical evidence.
    assert (
        questions["XC100"]["instructions"]["historical_evidence"]
        ["all_sites_all_months"]["observed_rate_percent"]
        == 0.0
    )


class FakeJevClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def __aenter__(self) -> FakeJevClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def system_one(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        answers = {
            target: SimpleNamespace(noul=max(0.02, 0.8 - 0.06 * index))
            for index, target in enumerate(TARGET_NAMES)
        }
        return SimpleNamespace(
            model=JEV_MODEL_VERSION,
            answers=answers,
            usage=SimpleNamespace(input_tokens=500, output_tokens=50),
        )


def test_jev_run_is_resumable_and_logs_only_complete_benchmark(tmp_path) -> None:
    prepared = _prepared_data()
    config = _config(str(tmp_path / "jev"))
    client = FakeJevClient()
    factory = lambda _: client

    partial = run_xc_jev(
        config,
        prepared_data=prepared,
        limit=1,
        client_factory=factory,
    )
    complete = run_xc_jev(
        config,
        prepared_data=prepared,
        client_factory=factory,
    )

    assert partial["run_scope"]["complete"] is False
    assert partial["metrics"]["evaluated_rows"] == 1
    assert complete["run_scope"]["complete"] is True
    assert complete["metrics"]["evaluated_rows"] == 2
    assert complete["metrics"]["input_tokens"] == 1000
    assert len(client.calls) == 2
    assert (tmp_path / "jev" / "evaluation.json").exists()
    assert len((tmp_path / "jev" / "predictions.jsonl").read_text().splitlines()) == 2
    probabilities = np.asarray(
        [complete["metrics"]["monotonic_violation_rate"]]
    )
    np.testing.assert_allclose(probabilities, 0.0)
