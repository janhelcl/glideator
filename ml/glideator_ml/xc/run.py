from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import torch

from ..tracking import log_experiment
from .benchmark import XCFeatureContract, frame_fingerprint, split_temporal
from .data import load_xc_data
from .evaluation import evaluate_predictions
from .onnx import export_xc_onnx, verify_onnx_parity
from .selection import split_development
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
        "validation_start": str(report["selection"]["validation_start"]),
        "train_end": str(benchmark["train_end"]),
        "eval_start": str(benchmark["eval_start"]),
        "eval_end": str(benchmark["eval_end"]),
    }


def run_xc(
    config: dict[str, Any],
    *,
    prepared_data: tuple[pd.DataFrame, XCFeatureContract] | None = None,
) -> dict[str, Any]:
    data_config = config["data"]
    model_config = config["model"]
    if str(data_config.get("split_strategy", "temporal")) != "temporal":
        raise ValueError("The migrated XC benchmark currently supports only temporal splits")

    frame, features = prepared_data or load_xc_data(data_config)
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

    validation_start = model_config.get("validation_start")
    if validation_start is None:
        raise ValueError(
            "model.validation_start is required so benchmark evaluation is never used for early stopping"
        )
    development = split_development(split.train, validation_start=validation_start)
    selection = {"validation_start": str(validation_start)}

    model_seed = int(model_config.get("seed", 42))
    benchmark_id = str(config["evaluation"].get("benchmark_id", "xc-temporal-v1"))
    git_sha = _git_sha()
    fit = fit_xc(development.fit, development.validation, features, model_config)
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
            "development_rows": len(split.train),
            "fit_rows": len(development.fit),
            "validation_rows": len(development.validation),
            "eval_rows": len(split.evaluation),
            "fit_sites": development.fit["site_id"].nunique(),
            "validation_sites": development.validation["site_id"].nunique(),
            "eval_sites": split.evaluation["site_id"].nunique(),
            "best_epoch": fit.best_epoch,
            "best_validation_loss": fit.best_validation_loss,
        }
    )

    artifact_config = config["artifact"]
    output_dir = Path(artifact_config.get("output_dir", "outputs/xc"))
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_path = output_dir / artifact_config.get("filename", "xc_checkpoint.pt")
    history_path = output_dir / "training_history.json"
    report_path = output_dir / "evaluation.json"
    artifact_paths = [checkpoint_path, history_path, report_path]

    onnx_metadata: dict[str, Any] = {"exported": False}
    if bool(artifact_config.get("export_onnx", False)):
        onnx_path = output_dir / artifact_config.get("onnx_filename", "model.onnx")
        opset_version = int(artifact_config.get("onnx_opset_version", 18))
        export_xc_onnx(fit.model, features, onnx_path, opset_version=opset_version)
        parity = verify_onnx_parity(
            fit.model,
            onnx_path,
            split.evaluation,
            features,
            sample_sizes=tuple(
                int(value)
                for value in config["evaluation"].get(
                    "onnx_parity_sample_sizes", [1, 7, 31]
                )
            ),
            atol=float(config["evaluation"].get("onnx_parity_atol", 1e-5)),
            rtol=float(config["evaluation"].get("onnx_parity_rtol", 1e-5)),
        )
        metrics.update(parity)
        artifact_paths.append(onnx_path)
        onnx_metadata = {
            "exported": True,
            "filename": onnx_path.name,
            "opset_version": opset_version,
            "parity_atol": float(config["evaluation"].get("onnx_parity_atol", 1e-5)),
            "parity_rtol": float(config["evaluation"].get("onnx_parity_rtol", 1e-5)),
        }

    metadata = {
        "task": "xc",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_id": benchmark_id,
        "dataset_fingerprint": dataset_fingerprint,
        "eval_set_fingerprint": eval_fingerprint,
        "model_seed": model_seed,
        "git_sha": git_sha,
        "benchmark": benchmark,
        "selection": selection,
        "weather_scaler_source_hour": 12,
        "onnx": onnx_metadata,
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
            "name": str(model_config.get("name", "expanded")),
            **fit.model_config,
        },
        "metrics": metrics,
    }
    _write_json(report_path, report)

    run_id = log_experiment(
        config=config,
        metrics=metrics,
        tags=_tracking_tags(config, report),
        artifacts=artifact_paths,
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
    required = [checkpoint_path, history_path, report_path]
    for path in required:
        if not path.is_file():
            raise FileNotFoundError(f"Missing XC experiment artifact: {path}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("mlflow_run_id"):
        return report
    artifacts = list(required)
    onnx_info = report.get("onnx", {})
    if onnx_info.get("exported"):
        onnx_path = output_dir / str(onnx_info["filename"])
        if not onnx_path.is_file():
            raise FileNotFoundError(f"Missing XC ONNX artifact: {onnx_path}")
        artifacts.append(onnx_path)
    run_id = log_experiment(
        config=config,
        metrics=report["metrics"],
        tags=_tracking_tags(config, report),
        artifacts=artifacts,
    )
    if run_id is None:
        raise RuntimeError("MLflow tracking is disabled; cannot backfill XC run")
    report["mlflow_run_id"] = run_id
    _write_json(report_path, report)
    return report
