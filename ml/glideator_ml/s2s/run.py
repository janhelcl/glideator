from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..tracking import log_experiment
from .artifact import S2SArtifact
from .asymmetric import fit_asymmetric
from .data import (
    dataset_fingerprint,
    events_fingerprint,
    load_visits,
    split_pilots,
    split_temporal,
    temporal_walk_forward_events,
    walk_forward_events,
)
from .deepsets import fit_deepsets
from .evaluation import evaluate
from .models import fit_contrastive, fit_svd


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _model_seed(config: dict[str, Any]) -> int:
    # Top-level seed is retained as a backward-compatible fallback for old configs.
    return int(config["model"].get("seed", config.get("seed", 42)))


def _split_seed(config: dict[str, Any]) -> int:
    # Split identity belongs to the data/benchmark, not to stochastic model training.
    return int(config["data"].get("split_seed", config.get("seed", 42)))


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _tracking_tags(
    config: dict[str, Any],
    report: dict[str, Any],
) -> dict[str, str]:
    benchmark = report["benchmark"]
    tags = {
        "task": "s2s",
        "model_family": str(
            config["model"].get(
                "name",
                report["model"].get("model_type", "svd"),
            )
        ),
        "benchmark_id": str(report["benchmark_id"]),
        "dataset_fingerprint": str(report["dataset_fingerprint"]),
        "eval_set_fingerprint": str(report["eval_set_fingerprint"]),
        "model_seed": str(report["model_seed"]),
        "git_sha": str(report["git_sha"]),
        "split_strategy": str(benchmark["split_strategy"]),
    }
    if "split_seed" in benchmark:
        tags["split_seed"] = str(benchmark["split_seed"])
    if "temporal_cutoff" in benchmark:
        tags["temporal_cutoff"] = str(benchmark["temporal_cutoff"])
    return tags


def _benchmark(
    config: dict[str, Any],
    visits,
):
    data = config["data"]
    strategy = str(data.get("split_strategy", "pilot"))
    min_history = int(data.get("min_eval_history", 1))

    if strategy == "pilot":
        split_seed = _split_seed(config)
        split = split_pilots(
            visits,
            eval_fraction=float(data.get("eval_fraction", 0.2)),
            seed=split_seed,
        )
        events = walk_forward_events(
            split.eval_visits,
            min_history=min_history,
        )
        metadata = {
            "split_strategy": "pilot",
            "split_seed": split_seed,
        }
    elif strategy == "temporal":
        cutoff = data.get("temporal_cutoff")
        if not cutoff:
            raise ValueError(
                "data.temporal_cutoff is required when split_strategy=temporal"
            )
        cutoff = str(cutoff)
        split = split_temporal(visits, cutoff=cutoff)
        events = temporal_walk_forward_events(
            visits,
            cutoff=cutoff,
            min_history=min_history,
        )
        metadata = {
            "split_strategy": "temporal",
            "temporal_cutoff": cutoff,
        }
    else:
        raise ValueError(f"Unsupported S2S split strategy: {strategy!r}")

    if not events:
        raise ValueError(
            f"S2S benchmark {strategy!r} produced no walk-forward evaluation events"
        )
    return split, events, metadata


def _fit(config: dict[str, Any], train_visits, metadata: dict[str, Any]) -> S2SArtifact:
    model = config["model"]
    name = model.get("name", "svd")
    seed = _model_seed(config)
    if name == "svd":
        return fit_svd(
            train_visits,
            n_factors=int(model.get("n_factors", 64)),
            sigma_power=float(model.get("sigma_power", 1.0)),
            seed=seed,
            metadata=metadata,
        )
    if name == "contrastive":
        return fit_contrastive(
            train_visits,
            n_factors=int(model.get("n_factors", 64)),
            epochs=int(model.get("epochs", 50)),
            learning_rate=float(model.get("learning_rate", 5e-3)),
            weight_decay=float(model.get("weight_decay", 1e-4)),
            temperature=float(model.get("temperature", 0.1)),
            batch_size=int(model.get("batch_size", 256)),
            negative_samples=int(model.get("negative_samples", 50)),
            negative_sampling_power=float(
                model.get("negative_sampling_power", 0.75)
            ),
            add_inbatch_negatives=bool(
                model.get("add_inbatch_negatives", False)
            ),
            device=str(model.get("device", "auto")),
            seed=seed,
            metadata=metadata,
        )
    if name == "deepsets":
        return fit_deepsets(
            train_visits,
            n_factors=int(model.get("n_factors", 64)),
            phi_hidden_dim=int(model.get("phi_hidden_dim", 128)),
            rho_hidden_dim=int(model.get("rho_hidden_dim", 128)),
            pooling=str(model.get("pooling", "mean")),
            epochs=int(model.get("epochs", 50)),
            learning_rate=float(model.get("learning_rate", 5e-3)),
            weight_decay=float(model.get("weight_decay", 1e-4)),
            temperature=float(model.get("temperature", 0.1)),
            batch_size=int(model.get("batch_size", 256)),
            negative_samples=int(model.get("negative_samples", 50)),
            negative_sampling_power=float(
                model.get("negative_sampling_power", 0.75)
            ),
            add_inbatch_negatives=bool(
                model.get("add_inbatch_negatives", False)
            ),
            device=str(model.get("device", "auto")),
            seed=seed,
            metadata=metadata,
        )
    if name == "asymmetric":
        return fit_asymmetric(
            train_visits,
            n_factors=int(model.get("n_factors", 64)),
            epochs=int(model.get("epochs", 50)),
            learning_rate=float(model.get("learning_rate", 5e-3)),
            weight_decay=float(model.get("weight_decay", 1e-4)),
            temperature=float(model.get("temperature", 0.1)),
            batch_size=int(model.get("batch_size", 256)),
            negative_samples=int(model.get("negative_samples", 50)),
            negative_sampling_power=float(
                model.get("negative_sampling_power", 0.75)
            ),
            add_inbatch_negatives=bool(
                model.get("add_inbatch_negatives", False)
            ),
            device=str(model.get("device", "auto")),
            seed=seed,
            metadata=metadata,
        )
    raise ValueError(f"Unsupported S2S model: {name!r}")


def run_s2s(config: dict[str, Any]) -> dict[str, Any]:
    visits = load_visits(config["data"])
    fingerprint = dataset_fingerprint(visits)
    model_seed = _model_seed(config)
    benchmark_id = str(config["evaluation"].get("benchmark_id", "s2s-v1"))

    split, events, benchmark_metadata = _benchmark(config, visits)
    eval_fingerprint = events_fingerprint(events)

    git_sha = _git_sha()
    model_metadata = {
        "task": "s2s",
        "dataset_fingerprint": fingerprint,
        "benchmark_id": benchmark_id,
        "eval_set_fingerprint": eval_fingerprint,
        "model_seed": model_seed,
        "git_sha": git_sha,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **benchmark_metadata,
    }
    artifact = _fit(config, split.train_visits, model_metadata)

    metrics = evaluate(
        artifact,
        events,
        split.train_visits,
        ks=[int(k) for k in config["evaluation"].get("ks", [5, 10])],
    )
    metrics.update(
        {
            "dataset_rows": len(visits),
            "train_rows": len(split.train_visits),
            "eval_rows": len(split.eval_visits),
            "train_pilots": split.train_visits["pilot"].nunique(),
            "eval_pilots": split.eval_visits["pilot"].nunique(),
        }
    )

    output_dir = Path(config["artifact"].get("output_dir", "outputs/s2s"))
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact.save(
        output_dir / config["artifact"].get("filename", "s2s_embeddings.pkl")
    )
    report_path = output_dir / "evaluation.json"
    report = {
        "task": "s2s",
        "benchmark_id": benchmark_id,
        "benchmark": benchmark_metadata,
        "dataset_fingerprint": fingerprint,
        "eval_set_fingerprint": eval_fingerprint,
        "model_seed": model_seed,
        "git_sha": git_sha,
        "model": artifact.metadata,
        "metrics": metrics,
    }
    if "split_seed" in benchmark_metadata:
        # Preserve the v1 report contract for existing comparisons/scripts.
        report["split_seed"] = benchmark_metadata["split_seed"]

    _write_report(report_path, report)

    run_id = log_experiment(
        config=config,
        metrics=metrics,
        tags=_tracking_tags(config, report),
        artifacts=[artifact_path, report_path],
    )
    report["mlflow_run_id"] = run_id
    if run_id is not None:
        _write_report(report_path, report)
    return report


def backfill_s2s_tracking(config: dict[str, Any]) -> dict[str, Any]:
    output_dir = Path(config["artifact"].get("output_dir", "outputs/s2s"))
    report_path = output_dir / "evaluation.json"
    artifact_path = output_dir / config["artifact"].get(
        "filename",
        "s2s_embeddings.pkl",
    )

    if not report_path.is_file():
        raise FileNotFoundError(f"Missing S2S evaluation report: {report_path}")
    if not artifact_path.is_file():
        raise FileNotFoundError(f"Missing S2S model artifact: {artifact_path}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("mlflow_run_id"):
        return report

    run_id = log_experiment(
        config=config,
        metrics=report["metrics"],
        tags=_tracking_tags(config, report),
        artifacts=[artifact_path, report_path],
    )
    if run_id is None:
        raise RuntimeError("MLflow tracking is disabled; cannot backfill S2S run")

    report["mlflow_run_id"] = run_id
    _write_report(report_path, report)
    return report
