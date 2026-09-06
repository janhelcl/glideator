from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch

from ..tracking import log_experiment
from .benchmark import frame_fingerprint, split_temporal
from .data import load_xc_data
from .evaluation import evaluate_predictions
from .training import fit_xc, predict_xc


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def _tracking_tags(config: dict[str, Any], report: dict[str, Any]) -> dict[str, str]:
    benchmark = report["benchmark"]
    return {
        "task": "xc",
        "model_family": str(config["model"].get("name", "expanded")),
        "benchmark_id": str(report["benchmark_id"]),
        "dataset_fingerprint": str(report["dataset_fingerprint"]),
        "eval_set_fingerprint": str(report["eval_set_fingerprint"]),
        "model_seed": str(report["model_seed"]),
        "git_sha": str(report["git_sha"]),
        "split_strategy": "temporal",
        "train_end": str(benchmark["train_end"]),
        "eval_start": str(benchmark["eval_start"]),
        "eval_end": str(benchmark["eval_end"]),
    }


def run_xc(config: dict[str, Any]) -> dict[str, Any]:
    data_config = config["data"]
    if str(data_config.get("split_strategy", "temporal")) != "temporal":
        raise ValueError("The migrated XC benchmark currently supports only temporal splits")

    frame, features = load_xc_data(data_config)
    dataset_fingerprint = frame_fingerprint(frame, features)
    benchmark = {
        "split_strategy": "temporal",
        "train_end": str(data_config["train_end"]),
        "eval_start": str(data_config["eval_start"]),
        "eval_end": str(data_config["eval_end"]),
    }
    split = split_temporal(
        frame,
        train_end=benchmark["train_end"],
        eval_start=benchmark["eval_start"],
        eval_end=benchmark["eval_end"],
        require_known_eval_sites=bool(data_config.get("require_known_eval_sites", True)),
    )
    eval_fingerprint = frame_fingerprint(split.evaluation, features)

    model_seed = int(config["model"].get("seed", 42))
    benchmark_id = str(config["evaluation"].get("benchmark_id", "xc-temporal-v1"))
    git_sha = _git_sha()
    fit = fit_xc(split.train, split.evaluation, features, config["model"])
    targets, probabilities = predict_xc(
        fit.model,
        split.evaluation,
        features,
        batch_size=int(config["evaluation"].get("batch_size", 4096)),
        device=fit.device,
    )
    metrics = evaluate_predictions(targets, probabilities)
    metrics.update(
        {
            "dataset_rows": len(frame),
            "train_rows": len(split.train),
            "eval_rows": len(split.evaluation),
            "train_sites": split.train["site_id"].nunique(),
            "eval_sites": split.evaluation["site_id"].nunique(),
            "best_epoch": fit.best_epoch,
            "best_validation_loss": fit.best_validation_loss,
        }
    )

    output_dir = Path(config["artifact"].get("output_dir", "outputs/xc"))
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / config["artifact"].get("filename", "xc_checkpoint.pt")
    history_path = output_dir / "training_history.json"
    report_path = output_dir / "evaluation.json"

    metadata = {
        "task": "xc",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_id": benchmark_id,
        "dataset_fingerprint": dataset_fingerprint,
        "eval_set_fingerprint": eval_fingerprint,
        "model_seed": model_seed,
        "git_sha": git_sha,
        "benchmark": benchmark,
        "weather_scaler_source_hour": 12,
    }
    checkpoint = {
        "format_version": 1,
        "model_class": "ExpandedGlideatorNet",
        "model_state_dict": {
            name: tensor.detach().cpu() for name, tensor in fit.model.state_dict().items()
        },
        "model_config": fit.model_config,
        "weather_scaling_params": fit.weather_scaling_params,
        "site_scaling_params": fit.site_scaling_params,
        "feature_contract": features.as_dict(),
        "metadata": metadata,
    }
    torch.save(checkpoint, checkpoint_path)
    _write_json(history_path, fit.history)

    report: dict[str, Any] = {
        **metadata,
        "feature_contract": features.as_dict(),
        "model": {
            "name": str(config["model"].get("name", "expanded")),
            **fit.model_config,
        },
        "metrics": metrics,
    }
    _write_json(report_path, report)

    run_id = log_experiment(
        config=config,
        metrics=metrics,
        tags=_tracking_tags(config, report),
        artifacts=[checkpoint_path, history_path, report_path],
    )
    report["mlflow_run_id"] = run_id
    if run_id is not None:
        _write_json(report_path, report)
    return report


def backfill_xc_tracking(config: dict[str, Any]) -> dict[str, Any]:
    output_dir = Path(config["artifact"].get("output_dir", "outputs/xc"))
    checkpoint_path = output_dir / config["artifact"].get("filename", "xc_checkpoint.pt")
    history_path = output_dir / "training_history.json"
    report_path = output_dir / "evaluation.json"
    for path in (checkpoint_path, history_path, report_path):
        if not path.is_file():
            raise FileNotFoundError(f"Missing XC experiment artifact: {path}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("mlflow_run_id"):
        return report
    run_id = log_experiment(
        config=config,
        metrics=report["metrics"],
        tags=_tracking_tags(config, report),
        artifacts=[checkpoint_path, history_path, report_path],
    )
    if run_id is None:
        raise RuntimeError("MLflow tracking is disabled; cannot backfill XC run")
    report["mlflow_run_id"] = run_id
    _write_json(report_path, report)
    return report
