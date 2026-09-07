from __future__ import annotations

import math

import pytest

from glideator_ml.cli import build_parser
from glideator_ml.xc.performance import BatchProfileResult, select_batch_size


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
        _result(8192, 190_000),
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
