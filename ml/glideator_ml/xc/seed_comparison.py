from __future__ import annotations

import copy
import json
from collections.abc import Sequence
from pathlib import Path
from statistics import fmean, stdev
from typing import Any

from .data import load_xc_data
from .run import run_xc


PRIMARY_METRICS = (
    "bce_macro",
    "brier_macro",
    "roc_auc_macro",
    "monotonic_violation_rate",
)
LOWER_IS_BETTER = {
    "bce_macro": True,
    "brier_macro": True,
    "roc_auc_macro": False,
    "monotonic_violation_rate": True,
}
IDENTITY_FIELDS = (
    "benchmark_id",
    "dataset_fingerprint",
    "eval_set_fingerprint",
)


def _seeded_config(config: dict[str, Any], seed: int) -> dict[str, Any]:
    """Return an isolated per-seed config without mutating the source config."""

    seeded = copy.deepcopy(config)
    model = seeded["model"]
    artifact = seeded["artifact"]

    model["seed"] = int(seed)
    model["name"] = f"{model.get('name', 'xc')}-seed-{seed}"

    base_output_dir = Path(str(artifact.get("output_dir", "outputs/xc")))
    artifact["output_dir"] = str(base_output_dir / "seed-sweep" / f"seed-{seed}")
    return seeded


def _assert_comparable(
    control_config: dict[str, Any], candidate_config: dict[str, Any]
) -> None:
    if control_config["data"] != candidate_config["data"]:
        raise ValueError("Seed comparison requires identical data configs")
    if control_config["evaluation"] != candidate_config["evaluation"]:
        raise ValueError("Seed comparison requires identical evaluation configs")


def _assert_run_identity(control: dict[str, Any], candidate: dict[str, Any]) -> None:
    for field in IDENTITY_FIELDS:
        if control[field] != candidate[field]:
            raise ValueError(
                f"Seed comparison identity mismatch for {field}: "
                f"{control[field]!r} != {candidate[field]!r}"
            )


def _run_metrics(report: dict[str, Any]) -> dict[str, float | int | str | None]:
    return {
        **{
            metric: float(report["metrics"][metric])
            for metric in PRIMARY_METRICS
        },
        "best_epoch": int(report["metrics"]["best_epoch"]),
        "trainable_parameters": int(report["metrics"]["trainable_parameters"]),
        "mlflow_run_id": report.get("mlflow_run_id"),
    }


def _metric_summary(
    pairs: list[dict[str, Any]], metric: str
) -> dict[str, float | int | None]:
    control_values = [float(pair["control"][metric]) for pair in pairs]
    candidate_values = [float(pair["candidate"][metric]) for pair in pairs]
    deltas = [
        candidate - control
        for control, candidate in zip(control_values, candidate_values, strict=True)
    ]
    lower_is_better = LOWER_IS_BETTER[metric]
    wins = sum(
        candidate < control if lower_is_better else candidate > control
        for control, candidate in zip(control_values, candidate_values, strict=True)
    )
    return {
        "control_mean": fmean(control_values),
        "candidate_mean": fmean(candidate_values),
        "mean_delta_candidate_minus_control": fmean(deltas),
        "delta_sample_std": stdev(deltas) if len(deltas) > 1 else None,
        "candidate_wins": wins,
        "seeds": len(deltas),
    }


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def _normalize_seeds(seeds: Sequence[int]) -> list[int]:
    normalized = [int(seed) for seed in seeds]
    if not normalized:
        raise ValueError("Seed comparison requires at least one seed")
    if len(set(normalized)) != len(normalized):
        raise ValueError("Seed comparison seeds must be unique")
    return normalized


def _run_seed_pairs(
    control_configs: Sequence[dict[str, Any]],
    candidate_config: dict[str, Any],
    *,
    seeds: Sequence[int],
) -> tuple[list[int], list[str], dict[str, list[dict[str, Any]]]]:
    controls = list(control_configs)
    if not controls:
        raise ValueError("Seed comparison requires at least one control config")
    normalized_seeds = _normalize_seeds(seeds)
    for control in controls:
        _assert_comparable(control, candidate_config)

    control_names = [str(control["model"].get("name", "xc-control")) for control in controls]
    if len(set(control_names)) != len(control_names):
        raise ValueError("Seed comparison control model names must be unique")

    prepared_data = load_xc_data(candidate_config["data"])
    pairs_by_control: dict[str, list[dict[str, Any]]] = {
        name: [] for name in control_names
    }

    for seed in normalized_seeds:
        candidate_report = run_xc(
            _seeded_config(candidate_config, seed), prepared_data=prepared_data
        )
        if int(candidate_report["model_seed"]) != seed:
            raise ValueError("Candidate run returned an unexpected model seed")
        candidate_metrics = _run_metrics(candidate_report)

        for control_name, control_config in zip(control_names, controls, strict=True):
            control_report = run_xc(
                _seeded_config(control_config, seed), prepared_data=prepared_data
            )
            _assert_run_identity(control_report, candidate_report)
            if int(control_report["model_seed"]) != seed:
                raise ValueError("Control run returned an unexpected model seed")

            pairs_by_control[control_name].append(
                {
                    "seed": seed,
                    "control": _run_metrics(control_report),
                    "candidate": candidate_metrics,
                }
            )

    return normalized_seeds, control_names, pairs_by_control


def _comparison_report(
    control_name: str,
    pairs: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "control_model": control_name,
        "pairs": pairs,
        "summary": {
            metric: _metric_summary(pairs, metric) for metric in PRIMARY_METRICS
        },
    }


def run_xc_seed_comparisons(
    control_configs: Sequence[dict[str, Any]],
    candidate_config: dict[str, Any],
    *,
    seeds: Sequence[int],
) -> dict[str, Any]:
    """Compare one candidate with several controls without retraining the candidate."""

    normalized_seeds, control_names, pairs_by_control = _run_seed_pairs(
        control_configs,
        candidate_config,
        seeds=seeds,
    )
    comparisons = [
        _comparison_report(control_name, pairs_by_control[control_name])
        for control_name in control_names
    ]
    report: dict[str, Any] = {
        "task": "xc",
        "comparison": "paired_seed_confirmation_multi_control",
        "control_models": control_names,
        "candidate_model": str(
            candidate_config["model"].get("name", "xc-candidate")
        ),
        "seeds": normalized_seeds,
        "benchmark_id": str(candidate_config["evaluation"]["benchmark_id"]),
        "comparisons": comparisons,
    }

    output_dir = Path(str(candidate_config["artifact"]["output_dir"])) / "seed-sweep"
    summary_path = output_dir / "paired_comparisons.json"
    _write_json(summary_path, report)
    report["summary_path"] = str(summary_path)
    return report


def run_xc_seed_comparison(
    control_config: dict[str, Any],
    candidate_config: dict[str, Any],
    *,
    seeds: Sequence[int],
) -> dict[str, Any]:
    """Run a paired multi-seed XC comparison on one prepared dataset snapshot."""

    normalized_seeds, control_names, pairs_by_control = _run_seed_pairs(
        [control_config],
        candidate_config,
        seeds=seeds,
    )
    comparison = _comparison_report(control_names[0], pairs_by_control[control_names[0]])
    report: dict[str, Any] = {
        "task": "xc",
        "comparison": "paired_seed_confirmation",
        "control_model": comparison["control_model"],
        "candidate_model": str(
            candidate_config["model"].get("name", "xc-candidate")
        ),
        "seeds": normalized_seeds,
        "benchmark_id": str(candidate_config["evaluation"]["benchmark_id"]),
        "pairs": comparison["pairs"],
        "summary": comparison["summary"],
    }

    output_dir = Path(str(candidate_config["artifact"]["output_dir"])) / "seed-sweep"
    summary_path = output_dir / "paired_comparison.json"
    _write_json(summary_path, report)
    report["summary_path"] = str(summary_path)
    return report
