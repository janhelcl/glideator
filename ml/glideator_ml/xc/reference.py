from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from ..tracking import log_experiment
from .benchmark import frame_fingerprint, split_temporal
from .data import load_xc_data
from .evaluation import evaluate_predictions
from .onnx import score_onnx
from .preprocessing import TARGET_NAMES


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return f"sha256:{hasher.hexdigest()}"


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def run_xc_onnx_reference(config: dict[str, Any]) -> dict[str, Any]:
    data_config = config["data"]
    if str(data_config.get("split_strategy", "temporal")) != "temporal":
        raise ValueError("XC ONNX reference evaluation supports only temporal benchmarks")

    frame, features = load_xc_data(data_config)
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
    dataset_fingerprint = frame_fingerprint(frame, features)
    eval_fingerprint = frame_fingerprint(split.evaluation, features)

    reference_config = config["reference"]
    onnx_path = Path(reference_config["onnx_path"])
    if not onnx_path.is_file():
        raise FileNotFoundError(f"Missing XC ONNX reference artifact: {onnx_path}")
    onnx_fingerprint = _file_sha256(onnx_path)

    probabilities = score_onnx(onnx_path, split.evaluation, features)
    targets = split.evaluation[list(TARGET_NAMES)].to_numpy(dtype=np.float32)
    metrics = evaluate_predictions(targets, probabilities)
    metrics.update(
        {
            "dataset_rows": len(frame),
            "train_rows": len(split.train),
            "eval_rows": len(split.evaluation),
            "train_sites": split.train["site_id"].nunique(),
            "eval_sites": split.evaluation["site_id"].nunique(),
        }
    )

    benchmark_id = str(config["evaluation"].get("benchmark_id", "xc-temporal-v1"))
    report: dict[str, Any] = {
        "task": "xc",
        "run_kind": "onnx-reference",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_id": benchmark_id,
        "dataset_fingerprint": dataset_fingerprint,
        "eval_set_fingerprint": eval_fingerprint,
        "git_sha": _git_sha(),
        "benchmark": benchmark,
        "feature_contract": features.as_dict(),
        "reference": {
            "name": str(reference_config.get("name", "served-production-onnx")),
            "onnx_path": str(onnx_path),
            "onnx_fingerprint": onnx_fingerprint,
        },
        "metrics": metrics,
    }

    output_dir = Path(config["artifact"].get("output_dir", "outputs/xc/served-reference"))
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "evaluation.json"
    _write_json(report_path, report)

    tags = {
        "task": "xc",
        "run_kind": "onnx-reference",
        "model_family": str(reference_config.get("name", "served-production-onnx")),
        "benchmark_id": benchmark_id,
        "dataset_fingerprint": dataset_fingerprint,
        "eval_set_fingerprint": eval_fingerprint,
        "reference_onnx_fingerprint": onnx_fingerprint,
        "git_sha": str(report["git_sha"]),
        "split_strategy": "temporal",
        "train_end": benchmark["train_end"],
        "eval_start": benchmark["eval_start"],
        "eval_end": benchmark["eval_end"],
    }
    run_id = log_experiment(
        config=config,
        metrics=metrics,
        tags=tags,
        artifacts=[onnx_path, report_path],
    )
    report["mlflow_run_id"] = run_id
    if run_id is not None:
        _write_json(report_path, report)
    return report
