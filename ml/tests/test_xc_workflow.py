from __future__ import annotations

import pytest

from glideator_ml.xc import workflow


def _candidate_config() -> dict:
    return {
        "task": "xc",
        "data": {
            "source": "database",
            "table": "glideator_fs.features_with_target",
            "start_date": "2021-01-01",
            "train_end": "2023-12-31",
            "eval_start": "2024-01-01",
            "eval_end": "2024-12-31",
        },
        "evaluation": {"benchmark_id": "xc-temporal-2024-v1"},
        "model": {},
        "artifact": {},
        "promotion": {},
        "tracking": {},
    }


def _reference_config() -> dict:
    candidate = _candidate_config()
    return {
        "task": "xc",
        "data": dict(candidate["data"]),
        "evaluation": {"benchmark_id": "xc-temporal-2024-v1"},
        "reference": {},
        "artifact": {},
        "tracking": {},
    }


def test_benchmark_workflow_uses_one_snapshot_for_reference_and_candidate(monkeypatch) -> None:
    calls: list[str] = []
    snapshot = object()
    received: list[object] = []

    monkeypatch.setattr(
        workflow,
        "load_xc_data",
        lambda config: calls.append("load") or snapshot,
    )

    def reference(config, *, prepared_data=None):
        calls.append("reference")
        received.append(prepared_data)
        return {"kind": "reference"}

    def candidate(config, *, prepared_data=None):
        calls.append("candidate")
        received.append(prepared_data)
        return {"kind": "candidate"}

    monkeypatch.setattr(workflow, "run_xc_onnx_reference", reference)
    monkeypatch.setattr(workflow, "run_xc", candidate)
    monkeypatch.setattr(
        workflow,
        "run_xc_promotion_check",
        lambda config: calls.append("promotion") or {"eligible": True},
    )

    result = workflow.run_xc_benchmark_workflow(
        _candidate_config(), _reference_config()
    )

    assert calls == ["load", "reference", "candidate", "promotion"]
    assert received == [snapshot, snapshot]
    assert result["eligible"] is True
    assert result["reference"] == {"kind": "reference"}
    assert result["candidate"] == {"kind": "candidate"}
    assert result["promotion"] == {"eligible": True}


def test_benchmark_workflow_rejects_different_data_contracts() -> None:
    reference = _reference_config()
    reference["data"]["eval_end"] = "2025-12-31"

    with pytest.raises(ValueError, match="same data section and benchmark_id"):
        workflow.run_xc_benchmark_workflow(_candidate_config(), reference)


def test_benchmark_workflow_rejects_different_benchmark_ids() -> None:
    reference = _reference_config()
    reference["evaluation"]["benchmark_id"] = "different-benchmark"

    with pytest.raises(ValueError, match="same data section and benchmark_id"):
        workflow.run_xc_benchmark_workflow(_candidate_config(), reference)
