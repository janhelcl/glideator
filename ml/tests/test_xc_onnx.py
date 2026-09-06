from __future__ import annotations

from pathlib import Path

import onnx
import onnxruntime as ort

from glideator_ml.xc.onnx import ONNX_INPUT_NAMES, ONNX_OUTPUT_NAME


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _model_path() -> Path:
    return _repo_root() / "backend" / "app" / "models" / "model.onnx"


def _initializer_shape(model: onnx.ModelProto, suffix: str) -> tuple[int, ...]:
    matches = [
        initializer
        for initializer in model.graph.initializer
        if initializer.name.endswith(suffix)
    ]
    assert len(matches) == 1, (
        f"Expected one ONNX initializer ending with {suffix!r}, found "
        f"{[initializer.name for initializer in matches]}"
    )
    return tuple(int(value) for value in matches[0].dims)


def test_checked_in_production_onnx_matches_migrated_io_contract() -> None:
    model_path = _model_path()
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


def test_checked_in_production_onnx_confirms_reference_architecture() -> None:
    model = onnx.load(_model_path())

    # 77 weather + 3 site + 32 site embedding + 4 date features = 116
    # features per time slice; three slices feed 348 values into the deep tower.
    assert _initializer_shape(model, "launch_embedding.weight") == (251, 32)
    assert _initializer_shape(model, "cross_net.kernels.0") == (116, 116)
    assert _initializer_shape(model, "cross_net.bias.0") == (116, 1)
    assert _initializer_shape(model, "cross_net.kernels.1") == (116, 116)
    assert _initializer_shape(model, "cross_net.bias.1") == (116, 1)

    assert _initializer_shape(model, "deep_net.0.weight") == (128, 348)
    assert _initializer_shape(model, "deep_net.0.bias") == (128,)
    assert _initializer_shape(model, "deep_net.2.weight") == (64, 128)
    assert _initializer_shape(model, "deep_net.2.bias") == (64,)
    assert _initializer_shape(model, "deep_net.4.weight") == (32, 64)
    assert _initializer_shape(model, "deep_net.4.bias") == (32,)

    assert _initializer_shape(model, "prediction_head.output_layers.0.weight") == (1, 32)
    assert _initializer_shape(model, "prediction_head.output_layers.10.weight") == (1, 32)

    initializer_names = [initializer.name for initializer in model.graph.initializer]
    assert not any("cross_nets." in name for name in initializer_names)
    assert not any("parallel_deep_net." in name for name in initializer_names)
