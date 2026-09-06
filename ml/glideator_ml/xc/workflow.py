from __future__ import annotations

from typing import Any

from .data import load_xc_data
from .promotion import run_xc_promotion_check
from .reference import run_xc_onnx_reference
from .run import run_xc


def _benchmark_identity(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "data": config["data"],
        "benchmark_id": str(config["evaluation"].get("benchmark_id", "xc-temporal-v1")),
    }


def run_xc_benchmark_workflow(
    candidate_config: dict[str, Any],
    reference_config: dict[str, Any],
) -> dict[str, Any]:
    """Run reference, candidate and promotion against one prepared data snapshot."""

    candidate_identity = _benchmark_identity(candidate_config)
    reference_identity = _benchmark_identity(reference_config)
    if candidate_identity != reference_identity:
        raise ValueError(
            "XC benchmark workflow requires candidate and reference configs to use "
            "the same data section and benchmark_id"
        )

    prepared_data = load_xc_data(candidate_config["data"])
    reference_report = run_xc_onnx_reference(
        reference_config, prepared_data=prepared_data
    )
    candidate_report = run_xc(candidate_config, prepared_data=prepared_data)
    promotion_report = run_xc_promotion_check(candidate_config)

    return {
        "task": "xc",
        "workflow": "reference-candidate-promotion",
        "eligible": bool(promotion_report["eligible"]),
        "reference": reference_report,
        "candidate": candidate_report,
        "promotion": promotion_report,
    }
