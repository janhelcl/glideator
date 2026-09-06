from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch

from .model import ExpandedGlideatorNet, StandardScalerLayer


def _initializers_by_suffix(model: Any) -> dict[str, np.ndarray]:
    from onnx import numpy_helper

    values: dict[str, np.ndarray] = {}
    for initializer in model.graph.initializer:
        array = np.asarray(numpy_helper.to_array(initializer))
        name = str(initializer.name)
        values[name] = array
    return values


def _unique_suffix(initializers: dict[str, np.ndarray], suffix: str) -> np.ndarray:
    matches = [value for name, value in initializers.items() if name.endswith(suffix)]
    if len(matches) != 1:
        names = [name for name in initializers if name.endswith(suffix)]
        raise ValueError(
            f"Expected one ONNX initializer ending with {suffix!r}, found {names}"
        )
    return matches[0]


def _scaler_from_arrays(means: np.ndarray, stds: np.ndarray) -> StandardScalerLayer:
    if means.ndim != 1 or stds.ndim != 1 or means.shape != stds.shape:
        raise ValueError("XC scaler means/stds must be equal-length vectors")
    params = {
        f"feature_{index}": {"mean": float(mean), "std": float(std)}
        for index, (mean, std) in enumerate(zip(means, stds, strict=True))
    }
    return StandardScalerLayer(params)


def load_migrated_model_from_onnx(path: str | Path) -> ExpandedGlideatorNet:
    """Reconstruct the migrated XC PyTorch model from a legacy production ONNX.

    This is a migration-validation tool, not a serving loader. It relies only on the
    parameter names and shapes embedded in the ONNX artifact, allowing us to prove
    that the TorchRec-free migrated architecture reproduces the currently served
    model numerically with the exact production weights.
    """

    import onnx

    graph = onnx.load(str(path))
    initializers = _initializers_by_suffix(graph)

    weather_means = _unique_suffix(initializers, "weather_scaler.means")
    weather_stds = _unique_suffix(initializers, "weather_scaler.stds")
    site_means = _unique_suffix(initializers, "site_scaler.means")
    site_stds = _unique_suffix(initializers, "site_scaler.stds")
    embedding = _unique_suffix(initializers, "launch_embedding.weight")
    if embedding.ndim != 2:
        raise ValueError("XC launch embedding must be a rank-2 matrix")

    cross_layers = 0
    while any(name.endswith(f"cross_net.kernels.{cross_layers}") for name in initializers):
        cross_layers += 1
    if cross_layers == 0:
        raise ValueError("Production XC ONNX does not contain a shared CrossNet")
    if any("cross_nets." in name for name in initializers):
        raise ValueError("Per-time CrossNets are not supported by production compatibility loader")
    if any("parallel_deep_net." in name for name in initializers):
        raise ValueError("Parallel deep tower is not supported by production compatibility loader")

    deep_hidden_units: list[int] = []
    layer_index = 0
    while True:
        suffix = f"deep_net.{layer_index}.weight"
        matches = [value for name, value in initializers.items() if name.endswith(suffix)]
        if not matches:
            break
        if len(matches) != 1 or matches[0].ndim != 2:
            raise ValueError(f"Invalid XC deep-layer initializer for {suffix}")
        deep_hidden_units.append(int(matches[0].shape[0]))
        layer_index += 2
    if not deep_hidden_units:
        raise ValueError("Production XC ONNX does not contain a deep tower")

    num_targets = sum(
        1
        for name in initializers
        if name.endswith(".weight") and "prediction_head.output_layers." in name
    )
    if num_targets == 0:
        raise ValueError("Production XC ONNX does not contain the multilabel prediction head")

    model = ExpandedGlideatorNet(
        weather_scaler=_scaler_from_arrays(weather_means, weather_stds),
        site_scaler=_scaler_from_arrays(site_means, site_stds),
        num_launches=int(embedding.shape[0]),
        num_targets=num_targets,
        deep_hidden_units=deep_hidden_units,
        cross_layers=cross_layers,
        site_embedding_dim=int(embedding.shape[1]),
        prediction_head_type="multilabel",
        parallel_deep_hidden_units=None,
        share_cross_net=True,
    )

    reconstructed: dict[str, torch.Tensor] = {}
    for state_name, state_value in model.state_dict().items():
        array = _unique_suffix(initializers, state_name)
        tensor = torch.from_numpy(np.array(array, copy=True)).to(dtype=state_value.dtype)
        if tensor.shape != state_value.shape:
            raise ValueError(
                f"ONNX initializer shape mismatch for {state_name}: "
                f"expected {tuple(state_value.shape)}, got {tuple(tensor.shape)}"
            )
        reconstructed[state_name] = tensor

    model.load_state_dict(reconstructed, strict=True)
    return model.eval()
