from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from glideator_ml.xc.reference import run_xc_onnx_reference


WEATHER_FEATURES = [f"f{index:02d}" for index in range(77)]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _raw_reference_frame() -> pd.DataFrame:
    rows = []
    for date_index, date in enumerate(("2023-06-01", "2024-06-01")):
        for site_id in (1, 2):
            row = {
                "site_id": site_id,
                "date": date,
                "max_points": float((date_index + site_id) * 20),
                "latitude": 49.5 + 0.1 * site_id,
                "longitude": 14.0 + 0.1 * site_id,
                "altitude": 300.0 + 50.0 * site_id,
            }
            for feature_index, feature in enumerate(WEATHER_FEATURES):
                for hour in (9, 12, 15):
                    row[f"{feature}_{hour}"] = (
                        0.01 * feature_index + 0.1 * hour + 0.05 * site_id
                    )
            rows.append(row)
    return pd.DataFrame(rows)


def test_served_onnx_can_be_scored_on_stable_xc_benchmark(tmp_path: Path) -> None:
    csv_path = tmp_path / "xc-reference.csv"
    _raw_reference_frame().to_csv(csv_path, index=False)
    output_dir = tmp_path / "reference-output"
    production_onnx = _repo_root() / "backend" / "app" / "models" / "model.onnx"
    config = {
        "task": "xc",
        "data": {
            "source": "csv",
            "path": str(csv_path),
            "start_date": "2023-01-01",
            "train_end": "2023-12-31",
            "eval_start": "2024-01-01",
            "eval_end": "2024-12-31",
            "split_strategy": "temporal",
            "require_known_eval_sites": True,
            "weather_features": WEATHER_FEATURES,
            "site_features": ["latitude", "longitude", "altitude"],
        },
        "evaluation": {"benchmark_id": "xc-test-reference-v1"},
        "reference": {
            "name": "served-production-onnx",
            "onnx_path": str(production_onnx),
        },
        "artifact": {"output_dir": str(output_dir)},
        "tracking": {"enabled": False},
    }

    report = run_xc_onnx_reference(config)

    assert report["run_kind"] == "onnx-reference"
    assert report["benchmark_id"] == "xc-test-reference-v1"
    assert report["metrics"]["train_rows"] == 2
    assert report["metrics"]["eval_rows"] == 2
    assert report["metrics"]["validation_loss"] > 0
    assert report["reference"]["onnx_fingerprint"].startswith("sha256:")
    assert report["mlflow_run_id"] is None

    persisted = json.loads((output_dir / "evaluation.json").read_text(encoding="utf-8"))
    assert persisted["reference"]["onnx_fingerprint"] == report["reference"]["onnx_fingerprint"]
