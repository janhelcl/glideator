from __future__ import annotations

from typing import Any

from .promotion import run_xc_promotion_check
from .reference import run_xc_onnx_reference
from .run import run_xc


def _benchmark_identity(config: dict[str, Any]) -> dict[str, Any]:
    data = config["data"]
    return {
        "data": data,
        "benchmark_id": str(config["evaluation"].get("benchmark_id", "xc-temporal-v1")),
    }


def run_xc_benchmark_workflow(
    candidate_config: dict[str, Any],
    reference_config: dict[str, Any],
) -> dict[str, Any]:
    """Run reference, candidate and promotion as one fail-safe workflow.

    Both configs must describe the same source query and benchmark identity. The
    final promotion comparator additionally verifies exact dataset and evaluation
    fingerprints, so a database mutation between the two reads fails closed rather
    than producing an invalid comparison.
    """

    candidate_identity = _benchmark_identity(candidate_config)
    reference_identity = _benchmark_identity(reference_config)
    if candidate_identity != reference_identity:
        raise ValueError(
            "XC benchmark workflow requires candidate and reference configs to use "
            "the same data section and benchmark_id"
        )

    reference_report = run_xc_onnx_reference(reference_config)
    candidate_report = run_xc(candidate_config)
    promotion_report = run_xc_promotion_check(candidate_config)

    return {
        "task": "xc",
        "workflow": "reference-candidate-promotion",
        "eligible": bool(promotion_report["eligible"]),
        "reference": reference_report,
        "candidate": candidate_report,
        "promotion": promotion_report,
    }
