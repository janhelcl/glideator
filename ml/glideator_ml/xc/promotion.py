from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_COMPARABILITY_FIELDS = (
    "benchmark_id",
    "dataset_fingerprint",
    "eval_set_fingerprint",
    "feature_contract",
)
_VALID_DIRECTIONS = {"lower", "higher"}


def _read_report(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing XC evaluation report: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"XC evaluation report must contain a JSON object: {path}")
    return value


def _metric(report: dict[str, Any], name: str, *, role: str) -> float:
    metrics = report.get("metrics")
    if not isinstance(metrics, dict) or name not in metrics:
        raise ValueError(f"{role} XC report is missing metric {name!r}")
    value = metrics[name]
    if not isinstance(value, (int, float)):
        raise ValueError(f"{role} XC metric {name!r} must be numeric")
    return float(value)


def compare_xc_reports(
    candidate: dict[str, Any],
    reference: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    mismatches = [
        field
        for field in _COMPARABILITY_FIELDS
        if candidate.get(field) != reference.get(field)
    ]

    result: dict[str, Any] = {
        "policy_version": str(policy.get("version", "xc-promotion-v1")),
        "comparable": not mismatches,
        "comparability_mismatches": mismatches,
        "eligible": False,
        "gates": {},
    }
    if mismatches:
        return result

    gates: dict[str, Any] = {}
    require_onnx_parity = bool(policy.get("require_candidate_onnx_parity", True))
    if require_onnx_parity:
        parity_limit = float(policy.get("onnx_parity_max_abs_diff", 1e-5))
        exported = bool(candidate.get("onnx", {}).get("exported", False))
        parity_value = _metric(
            candidate, "onnx_parity_max_abs_diff", role="candidate"
        ) if exported else None
        parity_passed = (
            exported and parity_value is not None and parity_value <= parity_limit
        )
        gates["onnx_parity"] = {
            "passed": parity_passed,
            "exported": exported,
            "value": parity_value,
            "maximum": parity_limit,
        }

    rules = policy.get("rules")
    if not isinstance(rules, dict) or not rules:
        raise ValueError("promotion.rules must contain at least one metric rule")

    for metric_name, rule in rules.items():
        if not isinstance(rule, dict):
            raise ValueError(f"Promotion rule for {metric_name!r} must be a mapping")
        direction = str(rule.get("direction", ""))
        if direction not in _VALID_DIRECTIONS:
            raise ValueError(
                f"Promotion rule for {metric_name!r} has invalid direction {direction!r}"
            )
        max_regression = float(rule.get("max_absolute_regression", 0.0))
        if max_regression < 0:
            raise ValueError("max_absolute_regression must be non-negative")

        candidate_value = _metric(candidate, metric_name, role="candidate")
        reference_value = _metric(reference, metric_name, role="reference")
        signed_delta = candidate_value - reference_value
        regression = signed_delta if direction == "lower" else -signed_delta
        passed = regression <= max_regression
        gates[metric_name] = {
            "passed": passed,
            "direction": direction,
            "candidate": candidate_value,
            "reference": reference_value,
            "delta_candidate_minus_reference": signed_delta,
            "regression": regression,
            "max_absolute_regression": max_regression,
        }

    result["gates"] = gates
    result["eligible"] = bool(gates) and all(
        bool(gate["passed"]) for gate in gates.values()
    )
    return result


def run_xc_promotion_check(config: dict[str, Any]) -> dict[str, Any]:
    promotion = config.get("promotion")
    if not isinstance(promotion, dict):
        raise ValueError("XC promotion check requires a promotion config section")

    candidate_path = Path(
        promotion.get(
            "candidate_report",
            Path(config["artifact"].get("output_dir", "outputs/xc")) / "evaluation.json",
        )
    )
    reference_path_value = promotion.get("reference_report")
    if not reference_path_value:
        raise ValueError("promotion.reference_report is required")
    reference_path = Path(reference_path_value)

    result = compare_xc_reports(
        _read_report(candidate_path),
        _read_report(reference_path),
        promotion,
    )
    result.update(
        {
            "task": "xc",
            "candidate_report": str(candidate_path),
            "reference_report": str(reference_path),
        }
    )

    output_path = Path(
        promotion.get(
            "output_path",
            Path(config["artifact"].get("output_dir", "outputs/xc"))
            / "promotion.json",
        )
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    return result
