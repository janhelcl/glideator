from __future__ import annotations

import math

import pytest

from glideator_ml.cli import build_parser
from glideator_ml.xc import performance as perf
from glideator_ml.xc.performance import (
    BatchProfileResult,
    batch_profile_metrics,
    select_batch_size,
)


def _result(batch_size: int, throughput: float | None, *, oom: bool = False):
    return BatchProfileResult(
        batch_size=batch_size,
        steps_per_epoch=math.ceil(181_040 / batch_size),
        samples_per_second=throughput,
        mean_step_ms=None,
        estimated_epoch_seconds=None,
        peak_allocated_gib=None,
        peak_reserved_gib=None,
        measured_steps=20 if throughput is not None else 0,
        measured_samples=batch_size * 20 if throughput is not None else 0,
        oom=oom,
        error="oom" if oom else None,
    )


def test_select_batch_size_uses_smallest_batch_near_peak_throughput() -> None:
    results = [
        _result(2048, 100_000),
        _result(4096, 150_000),
        _result(8192, 192_000),
        _result(16384, 200_000),
        _result(32768, 201_000),
    ]

    assert select_batch_size(results, throughput_fraction=0.95) == 8192


def test_select_batch_size_ignores_oom_results() -> None:
    results = [
        _result(8192, 180_000),
        _result(16384, 200_000),
        _result(32768, None, oom=True),
    ]

    assert select_batch_size(results, throughput_fraction=0.95) == 16384


def test_select_batch_size_requires_valid_fraction_and_success() -> None:
    with pytest.raises(ValueError, match="throughput_fraction"):
        select_batch_size([_result(2048, 10_000)], throughput_fraction=0.0)

    with pytest.raises(RuntimeError, match="No batch size"):
        select_batch_size([_result(2048, None, oom=True)])


def test_profile_batch_cli_defaults_cover_3090_sized_sweep() -> None:
    args = build_parser().parse_args(
        [
            "profile-batch",
            "xc",
            "--config",
            "configs/xc_production_reference.yaml",
        ]
    )

    assert args.batch_sizes == [2048, 4096, 8192, 16384, 32768, 65536]
    assert args.warmup_steps == 5
    assert args.steps == 20
    assert args.throughput_fraction == 0.95


def test_batch_profile_metrics_include_successful_and_oom_batches() -> None:
    report = {
        "recommended_batch_size": 8192,
        "best_throughput_batch_size": 16384,
        "fit_rows": 181040,
        "trainable_parameters": 12345,
        "throughput_fraction": 0.95,
        "results": [
            {
                "batch_size": 8192,
                "steps_per_epoch": 23,
                "oom": False,
                "samples_per_second": 190000.0,
                "mean_step_ms": 43.1,
                "estimated_epoch_seconds": 0.95,
                "peak_allocated_gib": 2.5,
                "peak_reserved_gib": 3.0,
            },
            {
                "batch_size": 65536,
                "steps_per_epoch": 3,
                "oom": True,
                "samples_per_second": None,
                "mean_step_ms": None,
                "estimated_epoch_seconds": None,
                "peak_allocated_gib": None,
                "peak_reserved_gib": None,
            },
        ],
    }

    metrics = batch_profile_metrics(report)

    assert metrics["recommended_batch_size"] == 8192
    assert metrics["bs8192_samples_per_second"] == 190000.0
    assert metrics["bs8192_oom"] == 0
    assert metrics["bs65536_oom"] == 1
    assert "bs65536_samples_per_second" not in metrics


def test_run_xc_batch_profile_logs_to_mlflow(tmp_path, monkeypatch) -> None:
    captured: dict = {}
    fake_report = {
        "recommended_batch_size": 8192,
        "best_throughput_batch_size": 16384,
        "fit_rows": 181040,
        "trainable_parameters": 12345,
        "throughput_fraction": 0.95,
        "device": {"name": "NVIDIA GeForce RTX 3090"},
        "results": [
            {
                "batch_size": 8192,
                "steps_per_epoch": 23,
                "oom": False,
                "samples_per_second": 190000.0,
                "mean_step_ms": 43.1,
                "estimated_epoch_seconds": 0.95,
                "peak_allocated_gib": 2.5,
                "peak_reserved_gib": 3.0,
            }
        ],
    }

    monkeypatch.setattr(perf, "load_xc_data", lambda config: ("frame", "features"))
    monkeypatch.setattr(
        perf,
        "split_temporal",
        lambda *args, **kwargs: type("Split", (), {"train": "train"})(),
    )
    monkeypatch.setattr(
        perf,
        "split_development",
        lambda *args, **kwargs: type("Dev", (), {"fit": "fit"})(),
    )
    monkeypatch.setattr(perf, "profile_batch_sizes", lambda *args, **kwargs: dict(fake_report))

    def fake_log_experiment(**kwargs):
        captured.update(kwargs)
        return "run-profile-1"

    monkeypatch.setattr(perf, "log_experiment", fake_log_experiment)

    config = {
        "task": "xc",
        "data": {
            "train_end": "2023-12-31",
            "eval_start": "2024-01-01",
            "eval_end": "2024-11-30",
            "require_known_eval_sites": True,
        },
        "model": {
            "name": "expanded-production-reference",
            "validation_start": "2023-01-01",
        },
        "artifact": {"output_dir": str(tmp_path)},
        "tracking": {"enabled": True, "experiment_name": "glideator-xc"},
    }

    report = perf.run_xc_batch_profile(config, batch_sizes=[8192])

    assert report["mlflow_run_id"] == "run-profile-1"
    assert captured["tags"]["run_kind"] == "gpu-batch-profile"
    assert captured["metrics"]["recommended_batch_size"] == 8192
    saved = tmp_path / "batch_profile.json"
    assert saved.is_file()
    assert captured["artifacts"] == [saved]
