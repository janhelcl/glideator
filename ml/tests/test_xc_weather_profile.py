from __future__ import annotations

from pathlib import Path

import pytest
import torch
from torch import nn

from glideator_ml.config import load_config
from glideator_ml.xc.benchmark import (
    PRESSURE_PROFILE_FEATURES,
    PRODUCTION_WEATHER_FEATURES,
    pressure_profile_indices,
)
from glideator_ml.xc.model import ExpandedGlideatorNet, StandardScalerLayer


ROOT = Path(__file__).parents[1]
BASELINE = ROOT / "configs" / "xc" / "baselines" / "conventional_mlp.yaml"
CANDIDATE = (
    ROOT
    / "configs"
    / "xc"
    / "architecture"
    / "weather_profiles"
    / "vertical_conv.yaml"
)
PROFILE_CONFIG_KEYS = {
    "weather_profile_encoder_type",
    "weather_profile_conv_channels",
    "weather_profile_embedding_dim",
    "weather_profile_kernel_size",
}


def _scaler(names: tuple[str, ...]) -> StandardScalerLayer:
    return StandardScalerLayer(
        {name: {"mean": 0.0, "std": 1.0} for name in names}
    )


def _without(mapping: dict, *keys: str) -> dict:
    return {key: value for key, value in mapping.items() if key not in keys}


def test_pressure_profile_indices_are_canonical_lower_to_upper_order() -> None:
    indices = pressure_profile_indices(PRODUCTION_WEATHER_FEATURES)
    selected = tuple(PRODUCTION_WEATHER_FEATURES[index] for index in indices)

    assert len(indices) == 65
    assert selected == PRESSURE_PROFILE_FEATURES
    assert selected[:3] == (
        "u_wind_1000hpa_ms",
        "u_wind_975hpa_ms",
        "u_wind_950hpa_ms",
    )
    assert selected[-1] == "geopotential_height_500hpa_m"


def test_pressure_profile_indices_require_complete_profile() -> None:
    incomplete = tuple(
        feature
        for feature in PRODUCTION_WEATHER_FEATURES
        if feature != "temperature_700hpa_k"
    )

    with pytest.raises(ValueError, match="full canonical profile"):
        pressure_profile_indices(incomplete)


def test_vertical_profile_branch_is_shared_and_added_to_existing_branches() -> None:
    profile_indices = pressure_profile_indices(PRODUCTION_WEATHER_FEATURES)
    model = ExpandedGlideatorNet(
        weather_scaler=_scaler(PRODUCTION_WEATHER_FEATURES),
        site_scaler=_scaler(("latitude", "longitude", "altitude")),
        num_launches=5,
        num_targets=11,
        deep_hidden_units=(8, 4),
        cross_layers=0,
        site_embedding_dim=3,
        parallel_deep_hidden_units=(6, 5),
        dropout=0.10,
        weather_profile_encoder_type="vertical_conv",
        weather_profile_indices=profile_indices,
        weather_profile_shape=(5, 13),
        weather_profile_conv_channels=(8, 8),
        weather_profile_embedding_dim=7,
        weather_profile_kernel_size=3,
    )

    assert model.weather_profile_encoder is not None
    first_fusion_layer = model.deep_net[0]
    assert isinstance(first_fusion_layer, nn.Linear)

    # Per time slice: 87 raw inputs + 5 MLP outputs + 7 profile outputs.
    assert first_fusion_layer.in_features == 3 * (87 + 5 + 7)

    features = {
        "weather": {
            key: torch.randn(4, len(PRODUCTION_WEATHER_FEATURES))
            for key in model.time_keys
        },
        "site": torch.randn(4, 3),
        "site_id": torch.tensor([0, 1, 2, 3]),
        "date": torch.tensor(
            [
                [0.0, 2026.0, 0.1, 0.9],
                [1.0, 2026.0, 0.2, 0.8],
                [0.0, 2025.0, 0.3, 0.7],
                [0.0, 2024.0, 0.4, 0.6],
            ]
        ),
    }
    assert model(features).shape == (4, 11)


def test_vertical_profile_config_changes_only_the_profile_branch() -> None:
    baseline = load_config(BASELINE)
    candidate = load_config(CANDIDATE)

    assert candidate["task"] == baseline["task"]
    assert candidate["data"] == baseline["data"]
    assert candidate["evaluation"] == baseline["evaluation"]
    assert candidate["tracking"] == baseline["tracking"]
    assert _without(candidate["artifact"], "output_dir") == _without(
        baseline["artifact"], "output_dir"
    )
    assert _without(candidate["model"], "name", *PROFILE_CONFIG_KEYS) == _without(
        baseline["model"], "name"
    )
    assert candidate["model"]["weather_profile_encoder_type"] == "vertical_conv"
    assert candidate["model"]["weather_profile_conv_channels"] == [8, 8]
    assert candidate["model"]["weather_profile_embedding_dim"] == 32
    assert candidate["model"]["weather_profile_kernel_size"] == 3
