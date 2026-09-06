from __future__ import annotations

from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch

from glideator_ml.xc.compatibility import load_migrated_model_from_onnx
from glideator_ml.xc.onnx import ONNX_INPUT_NAMES, ONNX_OUTPUT_NAME, XCOnnxWrapper


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


def test_migrated_pytorch_reproduces_served_onnx_with_production_weights() -> None:
    model_path = _model_path()
    migrated = load_migrated_model_from_onnx(model_path)
    wrapper = XCOnnxWrapper(migrated).eval()

    rng = np.random.default_rng(42)
    batch_size = 13
    inputs = {
        "weather_9": rng.normal(size=(batch_size, 77)).astype(np.float32),
        "weather_12": rng.normal(size=(batch_size, 77)).astype(np.float32),
        "weather_15": rng.normal(size=(batch_size, 77)).astype(np.float32),
        "site": np.column_stack(
            [
                rng.uniform(45.0, 52.0, batch_size),
                rng.uniform(5.0, 20.0, batch_size),
                rng.uniform(100.0, 2500.0, batch_size),
            ]
        ).astype(np.float32),
        "site_id": rng.integers(0, 251, size=batch_size, dtype=np.int64),
        "date": np.column_stack(
            [
                rng.integers(0, 2, size=batch_size),
                np.full(batch_size, 2024),
                rng.uniform(-1.0, 1.0, batch_size),
                rng.uniform(-1.0, 1.0, batch_size),
            ]
        ).astype(np.float32),
    }

    session = ort.InferenceSession(
        str(model_path),
        providers=["CPUExecutionProvider"],
    )
    served = session.run([ONNX_OUTPUT_NAME], inputs)[0]

    with torch.no_grad():
        reconstructed = wrapper(
            torch.from_numpy(inputs["weather_9"]),
            torch.from_numpy(inputs["weather_12"]),
            torch.from_numpy(inputs["weather_15"]),
            torch.from_numpy(inputs["site"]),
            torch.from_numpy(inputs["site_id"]),
            torch.from_numpy(inputs["date"]),
        ).numpy()

    np.testing.assert_allclose(reconstructed, served, atol=1e-5, rtol=1e-5)
