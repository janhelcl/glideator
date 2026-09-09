from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from .data import load_xc_data
from .run import run_xc


PRIMARY_METRICS = (
    "bce_macro",
    "brier_macro",
    "roc_auc_macro",
    "monotonic_violation_rate",
)
IDENTITY_FIELDS = (
    "benchmark_id",
    "dataset_fingerprint",
    "eval_set_fingerprint",
)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def _assert_sweep_contract(configs: Sequence[dict[str, Any]]) -> None:
    if len(configs) < 2:
        raise ValueError("XC sweep requires at least two configs")

    reference = configs[0]
    reference_seed = int(reference["model"].get("seed", 42))
    output_dirs: set[str] = set()

    for config in configs:
        if config["data"] != reference["data"]:
            raise ValueError("XC sweep requires identical data configs")
        if config["evaluation"] != reference["evaluation"]:
            raise ValueError("XC sweep requires identical evaluation configs")
        if int(config["model"].get("seed", 42)) != reference_seed:
            raise ValueError("XC sweep requires the same model seed for every config")

        output_dir = str(config["artifact"].get("output_dir", "outputs/xc"))
        if output_dir in output_dirs:
            raise ValueError(
                f"XC sweep requires unique artifact output dirs; duplicate: {output_dir}"
            )
        output_dirs.add(output_dir)


def _assert_run_identity(reference: dict[str, Any], candidate: dict[str, Any]) -> None:
    for field in IDENTITY_FIELDS:
        if reference[field] != candidate[field]:
            raise ValueError(
                f"XC sweep identity mismatch for {field}: "
                f"{reference[field]!r} != {candidate[field]!r}"
            )


def _result_row(config: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    model = config["model"]
    metrics = report["metrics"]
    return {
        "name": str(model.get("name", "xc")),
        "seed": int(report["model_seed"]),
        "learning_rate": float(model.get("learning_rate", 1e-3)),
        "l1_lambda": float(model.get("l1_lambda", 1e-9)),
        "l2_lambda": float(model.get("l2_lambda", 1e-9)),
        "dropout": float(model.get("dropout", 0.0)),
        **{metric: float(metrics[metric]) for metric in PRIMARY_METRICS},
        "best_epoch": int(metrics["best_epoch"]),
        "best_validation_loss": float(metrics["best_validation_loss"]),
        "training_seconds": float(metrics["training_seconds"]),
        "trainable_parameters": int(metrics["trainable_parameters"]),
        "mlflow_run_id": report.get("mlflow_run_id"),
        "artifact_output_dir": str(
            config["artifact"].get("output_dir", "outputs/xc")
        ),
    }


def run_xc_sweep(
    configs: Sequence[dict[str, Any]],
    *,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Run comparable XC configs against one prepared dataset snapshot."""

    normalized = list(configs)
    _assert_sweep_contract(normalized)
    prepared_data = load_xc_data(normalized[0]["data"])

    rows: list[dict[str, Any]] = []
    reference_report: dict[str, Any] | None = None
    for config in normalized:
        report = run_xc(config, prepared_data=prepared_data)
        if reference_report is None:
            reference_report = report
        else:
            _assert_run_identity(reference_report, report)
        rows.append(_result_row(config, report))

    if reference_report is None:  # pragma: no cover - guarded above
        raise RuntimeError("XC sweep produced no runs")

    report = {
        "task": "xc",
        "comparison": "config_sweep",
        "benchmark_id": reference_report["benchmark_id"],
        "dataset_fingerprint": reference_report["dataset_fingerprint"],
        "eval_set_fingerprint": reference_report["eval_set_fingerprint"],
        "seed": int(reference_report["model_seed"]),
        "results": rows,
    }
    summary_path = Path(output_dir) / "sweep_summary.json"
    _write_json(summary_path, report)
    report["summary_path"] = str(summary_path)
    return report
