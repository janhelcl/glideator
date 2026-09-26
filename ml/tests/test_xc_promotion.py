from __future__ import annotations

from copy import deepcopy

from glideator_ml.xc.promotion import compare_xc_reports


def _report() -> dict:
    return {
        "benchmark_id": "xc-temporal-2024-v1",
        "dataset_fingerprint": "sha256:data",
        "eval_set_fingerprint": "sha256:eval",
        "feature_contract": {
            "weather_features": ["w1", "w2"],
            "site_features": ["latitude", "longitude", "altitude"],
            "date_features": ["weekend", "year", "day_of_year_sin", "day_of_year_cos"],
            "target_names": [f"XC{value}" for value in range(0, 101, 10)],
        },
        "onnx": {"exported": True},
        "metrics": {
            "bce_macro": 0.30,
            "brier_macro": 0.09,
            "roc_auc_macro": 0.75,
            "onnx_parity_max_abs_diff": 1e-7,
        },
    }


def _policy() -> dict:
    return {
        "version": "xc-promotion-v1",
        "require_candidate_onnx_parity": True,
        "onnx_parity_max_abs_diff": 1e-5,
        "rules": {
            "bce_macro": {
                "direction": "lower",
                "max_absolute_regression": 0.0,
            },
            "brier_macro": {
                "direction": "lower",
                "max_absolute_regression": 0.0,
            },
            "roc_auc_macro": {
                "direction": "higher",
                "max_absolute_regression": 0.0,
            },
        },
    }


def test_promotion_gate_accepts_comparable_non_regressing_candidate() -> None:
    reference = _report()
    candidate = deepcopy(reference)
    candidate["metrics"]["bce_macro"] = 0.29
    candidate["metrics"]["brier_macro"] = 0.08
    candidate["metrics"]["roc_auc_macro"] = 0.76

    result = compare_xc_reports(candidate, reference, _policy())

    assert result["comparable"] is True
    assert result["eligible"] is True
    assert all(gate["passed"] for gate in result["gates"].values())


def test_promotion_gate_reports_quality_regression() -> None:
    reference = _report()
    candidate = deepcopy(reference)
    candidate["metrics"]["brier_macro"] = 0.10

    result = compare_xc_reports(candidate, reference, _policy())

    assert result["comparable"] is True
    assert result["eligible"] is False
    assert result["gates"]["brier_macro"]["passed"] is False
    assert result["gates"]["brier_macro"]["regression"] > 0


def test_promotion_gate_refuses_different_benchmark_identity() -> None:
    reference = _report()
    candidate = deepcopy(reference)
    candidate["eval_set_fingerprint"] = "sha256:other-eval"

    result = compare_xc_reports(candidate, reference, _policy())

    assert result["comparable"] is False
    assert result["eligible"] is False
    assert result["comparability_mismatches"] == ["eval_set_fingerprint"]
    assert result["gates"] == {}


def test_promotion_gate_requires_verified_candidate_onnx() -> None:
    reference = _report()
    candidate = deepcopy(reference)
    candidate["onnx"]["exported"] = False
    candidate["metrics"].pop("onnx_parity_max_abs_diff")

    result = compare_xc_reports(candidate, reference, _policy())

    assert result["eligible"] is False
    assert result["gates"]["onnx_parity"]["passed"] is False
