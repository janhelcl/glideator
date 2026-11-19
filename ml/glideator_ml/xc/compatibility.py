from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch

from .model import ExpandedGlideatorNet, StandardScalerLayer


def _initializers(model: Any) -> dict[str, np.ndarray]:
    from onnx import numpy_helper

    return {
        str(initializer.name): np.asarray(numpy_helper.to_array(initializer))
        for initializer in model.graph.initializer
    }


def _parameter_matches(name: str, parameter_name: str) -> bool:
    actual = name.split(".")
    expected = parameter_name.split(".")
    return len(actual) >= len(expected) and actual[-len(expected) :] == expected


def _unique_parameter(initializers: dict[str, np.ndarray], parameter_name: str) -> np.ndarray:
    names = [name for name in initializers if _parameter_matches(name, parameter_name)]
    if len(names) != 1:
        raise ValueError(
            f"Expected one ONNX initializer for {parameter_name!r}, found {names}"
        )
    return initializers[names[0]]


def _linear_hidden_units(
    initializers: dict[str, np.ndarray], module_name: str
) -> list[int]:
    hidden_units: list[int] = []
    layer_index = 0
    while True:
        parameter_name = f"{module_name}.{layer_index}.weight"
        names = [
            name for name in initializers if _parameter_matches(name, parameter_name)
        ]
        if not names:
            break
        if len(names) != 1:
            raise ValueError(
                f"Expected one ONNX initializer for {parameter_name!r}, found {names}"
            )
        value = initializers[names[0]]
        if value.ndim != 2:
            raise ValueError(f"Invalid rank for ONNX initializer {names[0]!r}")
        hidden_units.append(int(value.shape[0]))
        layer_index += 2
    return hidden_units


def _scaler_from_arrays(means: np.ndarray, stds: np.ndarray) -> StandardScalerLayer:
    if means.ndim != 1 or stds.ndim != 1 or means.shape != stds.shape:
        raise ValueError("XC scaler means/stds must be equal-length vectors")
    params = {
        f"feature_{index}": {"mean": float(mean), "std": float(std)}
        for index, (mean, std) in enumerate(zip(means, stds, strict=True))
    }
    return StandardScalerLayer(params)


def infer_migrated_architecture_from_onnx(path: str | Path) -> dict[str, Any]:
    """Infer the migrated ExpandedGlideatorNet constructor contract from ONNX weights."""

    import onnx

    initializers = _initializers(onnx.load(str(path)))
    embedding = _unique_parameter(initializers, "launch_embedding.weight")
    if embedding.ndim != 2:
        raise ValueError("XC launch embedding must be a rank-2 matrix")

    cross_layers = 0
    while any(
        _parameter_matches(name, f"cross_net.kernels.{cross_layers}")
        for name in initializers
    ):
        cross_layers += 1
    if cross_layers == 0:
        raise ValueError("Production XC ONNX does not contain a shared CrossNet")
    if any("cross_nets." in name for name in initializers):
        raise ValueError("Per-time CrossNets are not supported by production compatibility loader")

    deep_hidden_units = _linear_hidden_units(initializers, "deep_net")
    if not deep_hidden_units:
        raise ValueError("Production XC ONNX does not contain a deep tower")
    parallel_hidden_units = _linear_hidden_units(initializers, "parallel_deep_net")

    output_weight_names = [
        name
        for name in initializers
        if "prediction_head.output_layers." in name
        and name.split(".")[-1] == "weight"
    ]
    if not output_weight_names:
        raise ValueError("Production XC ONNX does not contain the multilabel prediction head")

    return {
        "num_launches": int(embedding.shape[0]),
        "num_targets": len(output_weight_names),
        "deep_hidden_units": deep_hidden_units,
        "cross_layers": cross_layers,
        "site_embedding_dim": int(embedding.shape[1]),
        "prediction_head_type": "multilabel",
        "parallel_deep_hidden_units": parallel_hidden_units or None,
        "share_cross_net": True,
    }


def load_migrated_model_from_onnx(path: str | Path) -> ExpandedGlideatorNet:
    """Reconstruct migrated XC PyTorch using the exact weights in a legacy ONNX.

    This is migration-validation tooling, not a serving loader. A successful numerical
    comparison against the served artifact proves the TorchRec-free model preserves
    the production architecture and forward semantics independently of retraining.
    """

    import onnx

    initializers = _initializers(onnx.load(str(path)))
    weather_means = _unique_parameter(initializers, "weather_scaler.means")
    weather_stds = _unique_parameter(initializers, "weather_scaler.stds")
    site_means = _unique_parameter(initializers, "site_scaler.means")
    site_stds = _unique_parameter(initializers, "site_scaler.stds")
    architecture = infer_migrated_architecture_from_onnx(path)

    model = ExpandedGlideatorNet(
        weather_scaler=_scaler_from_arrays(weather_means, weather_stds),
        site_scaler=_scaler_from_arrays(site_means, site_stds),
        **architecture,
    )

    reconstructed: dict[str, torch.Tensor] = {}
    for state_name, state_value in model.state_dict().items():
        array = _unique_parameter(initializers, state_name)
        tensor = torch.from_numpy(np.array(array, copy=True)).to(dtype=state_value.dtype)
        if tensor.shape != state_value.shape:
            raise ValueError(
                f"ONNX initializer shape mismatch for {state_name}: "
                f"expected {tuple(state_value.shape)}, got {tuple(tensor.shape)}"
            )
        reconstructed[state_name] = tensor

    model.load_state_dict(reconstructed, strict=True)
    return model.eval()
