from __future__ import annotations

from pathlib import Path

import onnxruntime as ort

from glideator_ml.xc.onnx import ONNX_INPUT_NAMES, ONNX_OUTPUT_NAME


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_checked_in_production_onnx_matches_migrated_io_contract() -> None:
    model_path = _repo_root() / "backend" / "app" / "models" / "model.onnx"
    assert model_path.is_file()

    session = ort.InferenceSession(
        str(model_path),
        providers=["CPUExecutionProvider"],
    )
    inputs = session.get_inputs()
    outputs = session.get_outputs()

    assert tuple(value.name for value in inputs) == ONNX_INPUT_NAMES
    assert tuple(value.name for value in outputs) == (ONNX_OUTPUT_NAME,)
    assert [value.type for value in inputs] == [
        "tensor(float)",
        "tensor(float)",
        "tensor(float)",
        "tensor(float)",
        "tensor(int64)",
        "tensor(float)",
    ]
    assert [value.shape[-1] for value in inputs if len(value.shape) == 2] == [77, 77, 77, 3, 4]
    assert len(inputs[4].shape) == 1
    assert outputs[0].shape[-1] == 11
