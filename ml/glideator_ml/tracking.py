from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .config import flatten_config


def _import_mlflow():
    try:
        import mlflow
    except ImportError as exc:
        raise RuntimeError(
            "MLflow tracking is enabled but MLflow is not installed. "
            "Install the tracking extra with: pip install -e '.[tracking]'"
        ) from exc
    return mlflow


def log_experiment(
    *,
    config: dict[str, Any],
    metrics: dict[str, float | int],
    tags: dict[str, str],
    artifacts: list[Path],
) -> str | None:
    tracking = config.get("tracking", {})
    if not tracking.get("enabled", True):
        return None

    mlflow = _import_mlflow()
    uri_env = tracking.get("tracking_uri_env", "MLFLOW_TRACKING_URI")
    tracking_uri = os.getenv(uri_env) or tracking.get("default_tracking_uri", "file:./mlruns")
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment(tracking.get("experiment_name", f"glideator-{config['task']}"))

    run_name = tracking.get("run_name")
    with mlflow.start_run(run_name=run_name) as run:
        params = {
            key: value
            for key, value in flatten_config(config).items()
            if value is not None
        }
        mlflow.log_params(params)
        mlflow.log_metrics({key: float(value) for key, value in metrics.items()})
        mlflow.set_tags(tags)
        for artifact in artifacts:
            mlflow.log_artifact(str(artifact))
        return run.info.run_id
