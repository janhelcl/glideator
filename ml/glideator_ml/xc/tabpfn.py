from __future__ import annotations

import gc
import json
import subprocess
import time
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..tracking import log_experiment
from .benchmark import XCFeatureContract, frame_fingerprint, split_temporal
from .data import load_xc_data
from .evaluation import evaluate_predictions
from .preprocessing import DATE_FEATURES, TARGET_NAMES, WEATHER_TIMES
from .selection import split_development


TABPFN_ORDINAL_TARGET_ENCODING = "ordinal-multiclass-cumulative"
TABPFN_INDEPENDENT_TARGET_ENCODING = "independent-binary"
TABPFN_TARGET_ENCODING = TABPFN_ORDINAL_TARGET_ENCODING
TABPFN_MODEL_VERSION = "v3"


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def tabular_feature_columns(features: XCFeatureContract) -> tuple[str, ...]:
    """Flatten the existing XC feature contract without changing feature semantics."""

    return (
        "site_id",
        *features.site_features,
        *DATE_FEATURES,
        *(column for hour in WEATHER_TIMES for column in features.weather_columns(hour)),
    )


def build_tabular_features(
    frame: pd.DataFrame,
    features: XCFeatureContract,
) -> pd.DataFrame:
    """Build raw TabPFN inputs; TabPFN owns scaling/encoding preprocessing."""

    result = frame.loc[:, list(tabular_feature_columns(features))].copy()
    # The neural model represents site_id with an embedding. Explicit categorical
    # treatment gives the tabular challenger the same site-identity information
    # without pretending the integer IDs are ordered numerical values.
    result["site_id"] = result["site_id"].astype(str).astype("category")
    return result


def ordinal_classes_from_targets(frame: pd.DataFrame) -> np.ndarray:
    """Encode the eleven nested XC labels as one equivalent 12-class target.

    The target vector contains no more information than XC0..XC100: class 0 means
    no threshold was exceeded, class 1 means only XC0 was exceeded, ..., and class
    11 means all thresholds were exceeded.
    """

    targets = frame.loc[:, list(TARGET_NAMES)].to_numpy(dtype=np.int8)
    if np.any((targets != 0) & (targets != 1)):
        raise ValueError("XC targets must be binary for TabPFN ordinal encoding")
    if np.any(targets[:, 1:] > targets[:, :-1]):
        raise ValueError("XC targets must be nested before TabPFN ordinal encoding")
    return targets.sum(axis=1, dtype=np.int64)


def threshold_probabilities_from_classes(
    classes: np.ndarray,
    class_probabilities: np.ndarray,
) -> np.ndarray:
    """Convert 12-class probabilities back to P(XC > threshold) outputs."""

    classes = np.asarray(classes)
    probabilities = np.asarray(class_probabilities, dtype=float)
    if probabilities.ndim != 2 or probabilities.shape[1] != len(classes):
        raise ValueError("TabPFN class probability shape does not match classes")

    num_buckets = len(TARGET_NAMES) + 1
    buckets = np.zeros((probabilities.shape[0], num_buckets), dtype=float)
    seen: set[int] = set()
    for source_index, value in enumerate(classes):
        bucket = int(value)
        if bucket < 0 or bucket >= num_buckets:
            raise ValueError(f"Unexpected TabPFN ordinal class: {value!r}")
        if bucket in seen:
            raise ValueError(f"Duplicate TabPFN ordinal class: {bucket}")
        seen.add(bucket)
        buckets[:, bucket] = probabilities[:, source_index]

    # XCk is true exactly when the ordinal bucket is above the bucket associated
    # with threshold k. Reverse cumulative probability therefore recovers all
    # eleven binary probabilities and is monotonic by construction.
    survival = np.cumsum(buckets[:, ::-1], axis=1)[:, ::-1]
    return survival[:, 1:]


def positive_class_probability(
    classes: np.ndarray,
    class_probabilities: np.ndarray,
) -> np.ndarray:
    """Extract P(y=1) from a binary classifier without assuming class order."""

    classes = np.asarray(classes)
    probabilities = np.asarray(class_probabilities, dtype=float)
    if probabilities.ndim != 2 or probabilities.shape[1] != len(classes):
        raise ValueError("TabPFN class probability shape does not match classes")

    positive = np.zeros(probabilities.shape[0], dtype=float)
    seen: set[int] = set()
    for source_index, value in enumerate(classes):
        binary_class = int(value)
        if binary_class not in {0, 1}:
            raise ValueError(f"Unexpected TabPFN binary class: {value!r}")
        if binary_class in seen:
            raise ValueError(f"Duplicate TabPFN binary class: {binary_class}")
        seen.add(binary_class)
        if binary_class == 1:
            positive = probabilities[:, source_index]
    return positive


def _predict_in_batches(
    classifier: Any,
    frame: pd.DataFrame,
    batch_size: int | None,
) -> np.ndarray:
    if batch_size is None or batch_size <= 0 or batch_size >= len(frame):
        return np.asarray(classifier.predict_proba(frame), dtype=float)

    chunks = [
        np.asarray(classifier.predict_proba(frame.iloc[start : start + batch_size]), dtype=float)
        for start in range(0, len(frame), batch_size)
    ]
    return np.concatenate(chunks, axis=0)


def _tabpfn_classifier(model_config: dict[str, Any]) -> Any:
    try:
        from tabpfn import TabPFNClassifier
        from tabpfn.constants import ModelVersion
    except ImportError as exc:  # pragma: no cover - exercised only without optional dep
        raise RuntimeError(
            "TabPFN benchmark dependencies are not installed. "
            "Install glideator-ml[tabpfn,tracking] (and xc if needed)."
        ) from exc

    requested_version = str(model_config.get("version", TABPFN_MODEL_VERSION)).lower()
    if requested_version not in {"v3", "3", "tabpfn-3"}:
        raise ValueError(
            "The frontier XC benchmark is pinned to TabPFN-3; "
            f"got model.version={requested_version!r}"
        )

    return TabPFNClassifier.create_default_for_version(
        ModelVersion.V3,
        n_estimators=model_config.get("n_estimators", "auto"),
        categorical_features_indices=[0],
        device=str(model_config.get("device", "auto")),
        ignore_pretraining_limits=bool(model_config.get("ignore_pretraining_limits", False)),
        fit_mode=str(model_config.get("fit_mode", "fit_preprocessors")),
        memory_saving_mode=model_config.get("memory_saving_mode", "auto"),
        random_state=int(model_config.get("seed", 42)),
        n_preprocessing_jobs=int(model_config.get("n_preprocessing_jobs", 1)),
        show_progress_bar=bool(model_config.get("show_progress_bar", True)),
    )


def _tracking_tags(config: dict[str, Any], report: dict[str, Any]) -> dict[str, str]:
    benchmark = report["benchmark"]
    model = report["model"]
    return {
        "task": "xc",
        "model_family": str(model["name"]),
        "foundation_model": "tabpfn",
        "foundation_model_version": str(model["version"]),
        "target_encoding": str(model["target_encoding"]),
        "benchmark_id": str(report["benchmark_id"]),
        "dataset_fingerprint": str(report["dataset_fingerprint"]),
        "eval_set_fingerprint": str(report["eval_set_fingerprint"]),
        "context_fingerprint": str(report["context_fingerprint"]),
        "model_seed": str(report["model_seed"]),
        "git_sha": str(report["git_sha"]),
        "split_strategy": "temporal",
        "context_policy": str(report["selection"]["context_policy"]),
        "train_end": str(benchmark["train_end"]),
        "eval_start": str(benchmark["eval_start"]),
        "eval_end": str(benchmark["eval_end"]),
    }


def _ordinal_predictions(
    *,
    x_context: pd.DataFrame,
    context: pd.DataFrame,
    x_evaluation: pd.DataFrame,
    model_config: dict[str, Any],
    prediction_batch_size: int | None,
) -> tuple[np.ndarray, dict[str, Any]]:
    y_context = ordinal_classes_from_targets(context)
    classifier = _tabpfn_classifier(model_config)

    fit_started = time.perf_counter()
    classifier.fit(x_context, y_context)
    fit_seconds = time.perf_counter() - fit_started

    predict_started = time.perf_counter()
    class_probabilities = _predict_in_batches(
        classifier,
        x_evaluation,
        prediction_batch_size,
    )
    prediction_seconds = time.perf_counter() - predict_started
    probabilities = threshold_probabilities_from_classes(
        np.asarray(classifier.classes_), class_probabilities
    )
    return probabilities, {
        "classifier_count": 1,
        "ordinal_class_count": len(np.unique(y_context)),
        "fit_seconds": fit_seconds,
        "prediction_seconds": prediction_seconds,
        "fit_predict_seconds": fit_seconds + prediction_seconds,
    }


def _independent_predictions(
    *,
    x_context: pd.DataFrame,
    context: pd.DataFrame,
    x_evaluation: pd.DataFrame,
    model_config: dict[str, Any],
    prediction_batch_size: int | None,
) -> tuple[np.ndarray, dict[str, Any]]:
    probabilities = np.empty((len(x_evaluation), len(TARGET_NAMES)), dtype=float)
    fit_seconds_by_threshold: dict[str, float] = {}
    prediction_seconds_by_threshold: dict[str, float] = {}
    constant_thresholds: list[str] = []

    for target_index, target_name in enumerate(TARGET_NAMES):
        y_context = context[target_name].to_numpy(dtype=np.int8)
        unique_classes = np.unique(y_context)
        if np.any((unique_classes != 0) & (unique_classes != 1)):
            raise ValueError(f"{target_name} must be binary for independent TabPFN")

        if len(unique_classes) == 1:
            probabilities[:, target_index] = float(unique_classes[0])
            fit_seconds_by_threshold[target_name] = 0.0
            prediction_seconds_by_threshold[target_name] = 0.0
            constant_thresholds.append(target_name)
            continue

        classifier = _tabpfn_classifier(model_config)
        fit_started = time.perf_counter()
        classifier.fit(x_context, y_context)
        fit_seconds_by_threshold[target_name] = time.perf_counter() - fit_started

        predict_started = time.perf_counter()
        class_probabilities = _predict_in_batches(
            classifier,
            x_evaluation,
            prediction_batch_size,
        )
        prediction_seconds_by_threshold[target_name] = time.perf_counter() - predict_started
        probabilities[:, target_index] = positive_class_probability(
            np.asarray(classifier.classes_), class_probabilities
        )

        del classifier
        gc.collect()

    fit_seconds = sum(fit_seconds_by_threshold.values())
    prediction_seconds = sum(prediction_seconds_by_threshold.values())
    return probabilities, {
        "classifier_count": len(TARGET_NAMES) - len(constant_thresholds),
        "constant_threshold_count": len(constant_thresholds),
        "constant_thresholds": constant_thresholds,
        "fit_seconds_by_threshold": fit_seconds_by_threshold,
        "prediction_seconds_by_threshold": prediction_seconds_by_threshold,
        "fit_seconds": fit_seconds,
        "prediction_seconds": prediction_seconds,
        "fit_predict_seconds": fit_seconds + prediction_seconds,
    }


def run_xc_tabpfn(
    config: dict[str, Any],
    *,
    prepared_data: tuple[pd.DataFrame, XCFeatureContract] | None = None,
) -> dict[str, Any]:
    """Run a pinned TabPFN-3 challenger on the canonical XC benchmark."""

    data_config = config["data"]
    model_config = config["model"]
    evaluation_config = config["evaluation"]
    if str(data_config.get("split_strategy", "temporal")) != "temporal":
        raise ValueError("The XC TabPFN benchmark supports only temporal splits")

    target_encoding = str(
        model_config.get("target_encoding", TABPFN_ORDINAL_TARGET_ENCODING)
    )
    if target_encoding not in {
        TABPFN_ORDINAL_TARGET_ENCODING,
        TABPFN_INDEPENDENT_TARGET_ENCODING,
    }:
        raise ValueError(
            "model.target_encoding must be "
            f"{TABPFN_ORDINAL_TARGET_ENCODING!r} or "
            f"{TABPFN_INDEPENDENT_TARGET_ENCODING!r}, got {target_encoding!r}"
        )

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
        require_eval_boundary_coverage=bool(
            data_config.get("require_eval_boundary_coverage", False)
        ),
    )
    eval_fingerprint = frame_fingerprint(split.evaluation, features)

    validation_start = model_config.get("validation_start")
    if validation_start is None:
        raise ValueError(
            "model.validation_start is required to define fit-parity context rows"
        )
    development = split_development(split.train, validation_start=validation_start)
    context_policy = str(model_config.get("context_policy", "fit_parity"))
    if context_policy == "fit_parity":
        context = development.fit
    elif context_policy == "all_pre_eval":
        context = split.train
    else:
        raise ValueError(
            "model.context_policy must be 'fit_parity' or 'all_pre_eval', "
            f"got {context_policy!r}"
        )
    context_fingerprint = frame_fingerprint(context, features)

    x_context = build_tabular_features(context, features)
    x_evaluation = build_tabular_features(split.evaluation, features)
    targets = split.evaluation.loc[:, list(TARGET_NAMES)].to_numpy(dtype=float)

    prediction_batch_size_value = evaluation_config.get("prediction_batch_size", 8192)
    prediction_batch_size = (
        None
        if prediction_batch_size_value is None
        else int(prediction_batch_size_value)
    )

    if target_encoding == TABPFN_ORDINAL_TARGET_ENCODING:
        probabilities, runtime = _ordinal_predictions(
            x_context=x_context,
            context=context,
            x_evaluation=x_evaluation,
            model_config=model_config,
            prediction_batch_size=prediction_batch_size,
        )
    else:
        probabilities, runtime = _independent_predictions(
            x_context=x_context,
            context=context,
            x_evaluation=x_evaluation,
            model_config=model_config,
            prediction_batch_size=prediction_batch_size,
        )

    metrics = evaluate_predictions(targets, probabilities)
    metrics.update(
        {
            "dataset_rows": len(frame),
            "development_rows": len(split.train),
            "fit_rows": len(development.fit),
            "validation_rows": len(development.validation),
            "context_rows": len(context),
            "eval_rows": len(split.evaluation),
            "context_sites": context["site_id"].nunique(),
            "eval_sites": split.evaluation["site_id"].nunique(),
            "tabular_feature_count": x_context.shape[1],
            "classifier_count": runtime["classifier_count"],
            "fit_seconds": runtime["fit_seconds"],
            "prediction_seconds": runtime["prediction_seconds"],
            "fit_predict_seconds": runtime["fit_predict_seconds"],
        }
    )
    if "ordinal_class_count" in runtime:
        metrics["ordinal_class_count"] = runtime["ordinal_class_count"]
    if "constant_threshold_count" in runtime:
        metrics["constant_threshold_count"] = runtime["constant_threshold_count"]

    try:
        tabpfn_package_version = package_version("tabpfn")
    except PackageNotFoundError:  # pragma: no cover
        tabpfn_package_version = "unknown"

    benchmark_id = str(
        evaluation_config.get("benchmark_id", "xc-temporal-2024-jan-nov-v1")
    )
    model_seed = int(model_config.get("seed", 42))
    metadata = {
        "task": "xc",
        "benchmark_id": benchmark_id,
        "dataset_fingerprint": dataset_fingerprint,
        "eval_set_fingerprint": eval_fingerprint,
        "context_fingerprint": context_fingerprint,
        "model_seed": model_seed,
        "git_sha": _git_sha(),
        "benchmark": benchmark,
        "selection": {
            "validation_start": str(validation_start),
            "context_policy": context_policy,
        },
    }
    report: dict[str, Any] = {
        **metadata,
        "feature_contract": features.as_dict(),
        "model": {
            "name": str(model_config.get("name", "xc-tabpfn3")),
            "family": "tabpfn",
            "version": TABPFN_MODEL_VERSION,
            "package_version": tabpfn_package_version,
            "target_encoding": target_encoding,
            "n_estimators": model_config.get("n_estimators", "auto"),
            "fit_mode": str(model_config.get("fit_mode", "fit_preprocessors")),
            "memory_saving_mode": model_config.get("memory_saving_mode", "auto"),
            "categorical_features": ["site_id"],
        },
        "runtime": runtime,
        "metrics": metrics,
    }

    output_dir = Path(config["artifact"].get("output_dir", "outputs/xc/tabpfn3"))
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "evaluation.json"
    _write_json(report_path, report)

    run_id = log_experiment(
        config=config,
        metrics=metrics,
        tags=_tracking_tags(config, report),
        artifacts=[report_path],
    )
    report["mlflow_run_id"] = run_id
    if run_id is not None:
        _write_json(report_path, report)
    return report
