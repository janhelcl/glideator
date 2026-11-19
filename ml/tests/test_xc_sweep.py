from __future__ import annotations

import json
from pathlib import Path

import pytest

from glideator_ml.xc import sweep


def _config(name: str, output_dir: Path) -> dict:
    return {
        "task": "xc",
        "data": {
            "source": "database",
            "table": "features",
            "train_end": "2023-12-31",
            "eval_start": "2024-01-01",
            "eval_end": "2024-11-30",
        },
        "model": {
            "name": name,
            "seed": 42,
            "learning_rate": 0.001,
            "l1_lambda": 1e-9,
            "l2_lambda": 1e-9,
            "dropout": 0.0,
        },
        "evaluation": {"benchmark_id": "xc-test-v1", "batch_size": 32},
        "artifact": {"output_dir": str(output_dir), "filename": "model.pt"},
        "tracking": {"enabled": False},
    }


def test_sweep_runs_configs_on_one_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    control = _config("control", tmp_path / "control")
    candidate = _config("candidate", tmp_path / "candidate")
    candidate["model"]["learning_rate"] = 0.002

    prepared = (object(), object())
    load_calls = 0
    run_calls: list[str] = []

    def fake_load_xc_data(data_config):
        nonlocal load_calls
        assert data_config == control["data"]
        load_calls += 1
        return prepared

    def fake_run_xc(config, *, prepared_data=None):
        assert prepared_data is prepared
        name = str(config["model"]["name"])
        run_calls.append(name)
        candidate_run = name == "candidate"
        return {
            "benchmark_id": "xc-test-v1",
            "dataset_fingerprint": "dataset-1",
            "eval_set_fingerprint": "eval-1",
            "model_seed": 42,
            "mlflow_run_id": f"run-{name}",
            "metrics": {
                "bce_macro": 0.15 if candidate_run else 0.16,
                "brier_macro": 0.049 if candidate_run else 0.050,
                "roc_auc_macro": 0.941 if candidate_run else 0.940,
                "monotonic_violation_rate": 0.021 if candidate_run else 0.020,
                "best_epoch": 30 if candidate_run else 40,
                "best_validation_loss": 1.2 if candidate_run else 1.3,
                "training_seconds": 10.0,
                "trainable_parameters": 48_500,
            },
        }

    monkeypatch.setattr(sweep, "load_xc_data", fake_load_xc_data)
    monkeypatch.setattr(sweep, "run_xc", fake_run_xc)

    report = sweep.run_xc_sweep(
        [control, candidate],
        output_dir=tmp_path / "summary",
    )

    assert load_calls == 1
    assert run_calls == ["control", "candidate"]
    assert report["seed"] == 42
    assert [row["name"] for row in report["results"]] == ["control", "candidate"]
    assert report["results"][1]["learning_rate"] == pytest.approx(0.002)
    assert report["results"][1]["bce_macro"] == pytest.approx(0.15)

    summary_path = Path(report["summary_path"])
    assert summary_path.is_file()
    saved = json.loads(summary_path.read_text(encoding="utf-8"))
    assert saved["comparison"] == "config_sweep"
    assert len(saved["results"]) == 2


def test_sweep_rejects_mismatched_contract(tmp_path: Path) -> None:
    control = _config("control", tmp_path / "control")
    candidate = _config("candidate", tmp_path / "candidate")
    candidate["evaluation"]["benchmark_id"] = "different"

    with pytest.raises(ValueError, match="identical evaluation configs"):
        sweep.run_xc_sweep([control, candidate], output_dir=tmp_path / "summary")


def test_sweep_rejects_seed_changes(tmp_path: Path) -> None:
    control = _config("control", tmp_path / "control")
    candidate = _config("candidate", tmp_path / "candidate")
    candidate["model"]["seed"] = 43

    with pytest.raises(ValueError, match="same model seed"):
        sweep.run_xc_sweep([control, candidate], output_dir=tmp_path / "summary")


def test_sweep_rejects_duplicate_artifact_dirs(tmp_path: Path) -> None:
    control = _config("control", tmp_path / "shared")
    candidate = _config("candidate", tmp_path / "shared")

    with pytest.raises(ValueError, match="unique artifact output dirs"):
        sweep.run_xc_sweep([control, candidate], output_dir=tmp_path / "summary")
