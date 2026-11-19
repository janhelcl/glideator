from __future__ import annotations

import copy
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
import torch

from .benchmark import XCFeatureContract
from .model import ExpandedGlideatorNet
from .preprocessing import DATE_FEATURES


ONNX_INPUT_NAMES = (
    "weather_9",
    "weather_12",
    "weather_15",
    "site",
    "site_id",
    "date",
)
ONNX_OUTPUT_NAME = "predictions"


class XCOnnxWrapper(torch.nn.Module):
    """Flatten the task-owned feature dictionary to the production ONNX contract."""

    def __init__(self, model: ExpandedGlideatorNet):
        super().__init__()
        self.model = model

    def forward(
        self,
        weather_9: torch.Tensor,
        weather_12: torch.Tensor,
        weather_15: torch.Tensor,
        site: torch.Tensor,
        site_id: torch.Tensor,
        date: torch.Tensor,
    ) -> torch.Tensor:
        return self.model(
            {
                "weather": {
                    "9": weather_9,
                    "12": weather_12,
                    "15": weather_15,
                },
                "site": site,
                "site_id": site_id,
                "date": date,
            }
        )


def onnx_inputs_from_frame(
    frame: pd.DataFrame,
    features: XCFeatureContract,
) -> dict[str, np.ndarray]:
    return {
        "weather_9": frame[list(features.weather_columns(9))].to_numpy(dtype=np.float32),
        "weather_12": frame[list(features.weather_columns(12))].to_numpy(dtype=np.float32),
        "weather_15": frame[list(features.weather_columns(15))].to_numpy(dtype=np.float32),
        "site": frame[list(features.site_features)].to_numpy(dtype=np.float32),
        "site_id": frame["site_id"].to_numpy(dtype=np.int64),
        "date": frame[list(DATE_FEATURES)].to_numpy(dtype=np.float32),
    }


def _dummy_inputs(
    features: XCFeatureContract,
    *,
    batch_size: int = 2,
) -> tuple[torch.Tensor, ...]:
    weather_dim = len(features.weather_features)
    site_dim = len(features.site_features)
    return (
        torch.randn(batch_size, weather_dim, dtype=torch.float32),
        torch.randn(batch_size, weather_dim, dtype=torch.float32),
        torch.randn(batch_size, weather_dim, dtype=torch.float32),
        torch.randn(batch_size, site_dim, dtype=torch.float32),
        torch.zeros(batch_size, dtype=torch.int64),
        torch.tensor(
            [[0.0, 2024.0, 0.0, 1.0]] * batch_size,
            dtype=torch.float32,
        ),
    )


def export_xc_onnx(
    model: ExpandedGlideatorNet,
    features: XCFeatureContract,
    output_path: str | Path,
    *,
    opset_version: int = 18,
) -> Path:
    """Export a single-file, dynamic-batch ONNX artifact with production I/O names."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    export_model = copy.deepcopy(model).cpu().eval()
    wrapper = XCOnnxWrapper(export_model).eval()
    args = _dummy_inputs(features)
    batch = torch.export.Dim("batch", min=1)
    dynamic_shapes = {name: {0: batch} for name in ONNX_INPUT_NAMES}

    torch.onnx.export(
        wrapper,
        args,
        str(output),
        input_names=list(ONNX_INPUT_NAMES),
        output_names=[ONNX_OUTPUT_NAME],
        opset_version=opset_version,
        dynamo=True,
        external_data=False,
        dynamic_shapes=dynamic_shapes,
    )

    import onnx

    onnx.checker.check_model(onnx.load(str(output)))
    return output


def score_onnx(
    onnx_path: str | Path,
    frame: pd.DataFrame,
    features: XCFeatureContract,
) -> np.ndarray:
    import onnxruntime as ort

    session = ort.InferenceSession(
        str(onnx_path),
        providers=["CPUExecutionProvider"],
    )
    actual_inputs = tuple(value.name for value in session.get_inputs())
    if actual_inputs != ONNX_INPUT_NAMES:
        raise ValueError(
            f"XC ONNX input contract mismatch: expected {ONNX_INPUT_NAMES}, got {actual_inputs}"
        )
    outputs = session.run([ONNX_OUTPUT_NAME], onnx_inputs_from_frame(frame, features))
    return np.asarray(outputs[0], dtype=np.float32)


def pytorch_predictions(
    model: ExpandedGlideatorNet,
    frame: pd.DataFrame,
    features: XCFeatureContract,
) -> np.ndarray:
    inputs = onnx_inputs_from_frame(frame, features)
    tensors = {
        "weather": {
            "9": torch.from_numpy(inputs["weather_9"]),
            "12": torch.from_numpy(inputs["weather_12"]),
            "15": torch.from_numpy(inputs["weather_15"]),
        },
        "site": torch.from_numpy(inputs["site"]),
        "site_id": torch.from_numpy(inputs["site_id"]),
        "date": torch.from_numpy(inputs["date"]),
    }
    cpu_model = copy.deepcopy(model).cpu().eval()
    with torch.no_grad():
        return cpu_model(tensors).numpy()


def verify_onnx_parity(
    model: ExpandedGlideatorNet,
    onnx_path: str | Path,
    frame: pd.DataFrame,
    features: XCFeatureContract,
    *,
    sample_sizes: Sequence[int] = (1, 7, 31),
    atol: float = 1e-5,
    rtol: float = 1e-5,
) -> dict[str, float]:
    """Fail the export gate unless ONNX Runtime matches PyTorch on real rows."""

    if frame.empty:
        raise ValueError("Cannot verify XC ONNX parity on an empty frame")
    max_abs = 0.0
    max_rel = 0.0
    checked_rows = 0
    for requested in sample_sizes:
        count = min(int(requested), len(frame))
        if count <= 0:
            continue
        sample = frame.iloc[:count]
        expected = pytorch_predictions(model, sample, features)
        actual = score_onnx(onnx_path, sample, features)
        absolute = np.abs(expected - actual)
        relative = absolute / np.maximum(np.abs(expected), atol)
        max_abs = max(max_abs, float(absolute.max(initial=0.0)))
        max_rel = max(max_rel, float(relative.max(initial=0.0)))
        checked_rows += count
        np.testing.assert_allclose(actual, expected, atol=atol, rtol=rtol)
    return {
        "onnx_parity_max_abs_diff": max_abs,
        "onnx_parity_max_rel_diff": max_rel,
        "onnx_parity_checked_rows": float(checked_rows),
    }
