from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..tracking import log_experiment
from .artifact import S2SArtifact
from .data import (
    dataset_fingerprint,
    load_visits,
    split_pilots,
    walk_forward_events,
)
from .evaluation import evaluate
from .models import fit_svd


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _fit(config: dict[str, Any], train_visits, metadata: dict[str, Any]) -> S2SArtifact:
    model = config["model"]
    name = model.get("name", "svd")
    if name != "svd":
        raise ValueError(f"Unsupported S2S model: {name!r}")
    return fit_svd(
        train_visits,
        n_factors=int(model.get("n_factors", 64)),
        sigma_power=float(model.get("sigma_power", 1.0)),
        seed=int(config.get("seed", 42)),
        metadata=metadata,
    )


def run_s2s(config: dict[str, Any]) -> dict[str, Any]:
    visits = load_visits(config["data"])
    fingerprint = dataset_fingerprint(visits)
    seed = int(config.get("seed", 42))
    split = split_pilots(
        visits,
        eval_fraction=float(config["data"].get("eval_fraction", 0.2)),
        seed=seed,
    )
    events = walk_forward_events(
        split.eval_visits,
        min_history=int(config["data"].get("min_eval_history", 1)),
    )

    git_sha = _git_sha()
    model_metadata = {
        "task": "s2s",
        "dataset_fingerprint": fingerprint,
        "git_sha": git_sha,
        "created_at": datetime.now(timezone.utc).isoformat(),
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
        "dataset_fingerprint": fingerprint,
        "git_sha": git_sha,
        "model": artifact.metadata,
        "metrics": metrics,
    }
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    run_id = log_experiment(
        config=config,
        metrics=metrics,
        tags={
            "task": "s2s",
            "model_family": str(config["model"].get("name", "svd")),
            "dataset_fingerprint": fingerprint,
            "git_sha": git_sha,
        },
        artifacts=[artifact_path, report_path],
    )
    report["mlflow_run_id"] = run_id
    return report
