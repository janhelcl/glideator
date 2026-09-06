from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from glideator_ml.xc.benchmark import frame_fingerprint, split_temporal
from glideator_ml.xc.data import fit_scaling_params, prepare_xc_data
from glideator_ml.xc.evaluation import evaluate_predictions
from glideator_ml.xc.run import run_xc


def _raw_frame() -> pd.DataFrame:
    rows = []
    dates = ["2023-01-01", "2023-06-01", "2024-01-01", "2024-06-01"]
    points = {1: [0.0, 30.0, 5.0, 80.0], 2: [15.0, 60.0, 0.0, 120.0]}
    for date_index, date in enumerate(dates):
        for site_id in (1, 2):
            base = 10.0 * date_index + site_id
            row = {
                "site_id": site_id,
                "date": date,
                "max_points": points[site_id][date_index],
                "latitude": 49.0 + site_id,
                "longitude": 13.0 + site_id,
                "altitude": 300.0 + 100.0 * site_id,
            }
            for hour in (9, 12, 15):
                row[f"w1_{hour}"] = base + hour
                row[f"w2_{hour}"] = 2.0 * base + hour
            rows.append(row)
    return pd.DataFrame(rows)


def _data_config() -> dict:
    return {
        "source": "csv",
        "start_date": "2023-01-01",
        "train_end": "2023-12-31",
        "eval_start": "2024-01-01",
        "eval_end": "2024-12-31",
        "weather_features": ["w1", "w2"],
        "site_features": ["latitude", "longitude", "altitude"],
    }


def test_xc_temporal_benchmark_is_stable_and_row_order_independent() -> None:
    frame, features = prepare_xc_data(_raw_frame(), _data_config())
    split = split_temporal(
        frame,
        train_end="2023-12-31",
        eval_start="2024-01-01",
        eval_end="2024-12-31",
    )

    assert split.train["date"].max() == pd.Timestamp("2023-06-01")
    assert split.evaluation["date"].min() == pd.Timestamp("2024-01-01")
    fingerprint = frame_fingerprint(frame, features)
    shuffled = frame.sample(frac=1.0, random_state=123).reset_index(drop=True)
    assert frame_fingerprint(shuffled, features) == fingerprint


def test_xc_scaler_uses_noon_weather_slice_only() -> None:
    frame, features = prepare_xc_data(_raw_frame(), _data_config())
    split = split_temporal(
        frame,
        train_end="2023-12-31",
        eval_start="2024-01-01",
        eval_end="2024-12-31",
    )
    weather, site = fit_scaling_params(split.train, features)

    assert set(weather) == {"w1_12", "w2_12"}
    assert weather["w1_12"]["mean"] == split.train["w1_12"].mean()
    assert weather["w1_12"]["std"] == split.train["w1_12"].std(ddof=1)
    assert set(site) == {"latitude", "longitude", "altitude"}


def test_xc_evaluation_reports_probability_and_monotonicity_metrics() -> None:
    targets = np.zeros((4, 11), dtype=np.float32)
    targets[1:, 0] = 1.0
    probabilities = np.full((4, 11), 0.2, dtype=np.float32)
    probabilities[:, 0] = [0.1, 0.6, 0.7, 0.8]
    probabilities[:, 1] = [0.3, 0.5, 0.4, 0.2]

    metrics = evaluate_predictions(targets, probabilities)

    assert metrics["validation_loss"] > 0
    assert metrics["brier_macro"] >= 0
    assert 0 <= metrics["monotonic_violation_rate"] <= 1
    assert "roc_auc_XC0" in metrics


def test_run_xc_writes_reproducible_checkpoint_and_report(tmp_path: Path) -> None:
    csv_path = tmp_path / "xc.csv"
    _raw_frame().to_csv(csv_path, index=False)
    output_dir = tmp_path / "output"
    config = {
        "task": "xc",
        "data": {
            **_data_config(),
            "path": str(csv_path),
            "split_strategy": "temporal",
            "require_known_eval_sites": True,
        },
        "model": {
            "name": "test-expanded",
            "seed": 7,
            "deterministic": True,
            "device": "cpu",
            "num_launches": 3,
            "site_embedding_dim": 2,
            "deep_hidden_units": [8, 4],
            "cross_layers": 1,
            "prediction_head_type": "multilabel",
            "share_cross_net": True,
            "batch_size": 4,
            "learning_rate": 0.001,
            "lr_decay": 1.0,
            "epochs": 2,
            "patience": None,
            "l1_lambda": 0.0,
            "l2_lambda": 0.0,
            "monotonicity_lambda": 0.0,
        },
        "evaluation": {"benchmark_id": "xc-test-v1", "batch_size": 8},
        "artifact": {"output_dir": str(output_dir), "filename": "xc_checkpoint.pt"},
        "tracking": {"enabled": False},
    }

    report = run_xc(config)

    assert report["benchmark_id"] == "xc-test-v1"
    assert report["benchmark"]["split_strategy"] == "temporal"
    assert report["metrics"]["train_rows"] == 4
    assert report["metrics"]["eval_rows"] == 4
    assert report["mlflow_run_id"] is None

    checkpoint_path = output_dir / "xc_checkpoint.pt"
    evaluation_path = output_dir / "evaluation.json"
    history_path = output_dir / "training_history.json"
    assert checkpoint_path.is_file()
    assert evaluation_path.is_file()
    assert history_path.is_file()

    checkpoint = torch.load(checkpoint_path, weights_only=False)
    assert checkpoint["format_version"] == 1
    assert checkpoint["model_config"]["num_launches"] == 3
    assert checkpoint["metadata"]["weather_scaler_source_hour"] == 12
    persisted = json.loads(evaluation_path.read_text(encoding="utf-8"))
    assert persisted["dataset_fingerprint"] == report["dataset_fingerprint"]
