from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import torch
from torch import nn

from glideator_ml.config import load_config
from glideator_ml.xc.benchmark import (
    PRESSURE_LEVELS_HPA,
    PRESSURE_PROFILE_FEATURES,
    PRODUCTION_WEATHER_FEATURES,
    XCFeatureContract,
    pressure_profile_indices,
)
from glideator_ml.xc.model import ExpandedGlideatorNet, StandardScalerLayer
from glideator_ml.xc.training import _profile_agl_scaling


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
AGL_CANDIDATE = (
    ROOT
    / "configs"
    / "xc"
    / "architecture"
    / "weather_profiles"
    / "vertical_conv_agl_mask.yaml"
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


def test_agl_profile_uses_raw_site_height_and_masks_below_ground_levels() -> None:
    profile_indices = pressure_profile_indices(PRODUCTION_WEATHER_FEATURES)
    surface_pressure_index = PRODUCTION_WEATHER_FEATURES.index("pressure_sfc_pa")
    model = ExpandedGlideatorNet(
        weather_scaler=_scaler(PRODUCTION_WEATHER_FEATURES),
        site_scaler=_scaler(("latitude", "longitude", "altitude")),
        num_launches=2,
        num_targets=11,
        deep_hidden_units=(8, 4),
        cross_layers=0,
        site_embedding_dim=3,
        parallel_deep_hidden_units=(6, 5),
        weather_profile_encoder_type="vertical_conv",
        weather_profile_indices=profile_indices,
        weather_profile_shape=(5, 13),
        weather_profile_conv_channels=(8, 8),
        weather_profile_embedding_dim=7,
        weather_profile_kernel_size=3,
        weather_profile_use_agl_mask=True,
        weather_profile_surface_pressure_index=surface_pressure_index,
        weather_profile_site_altitude_index=2,
        weather_profile_pressure_levels_hpa=PRESSURE_LEVELS_HPA,
        weather_profile_agl_means=[0.0] * 13,
        weather_profile_agl_stds=[1.0] * 13,
    )
    model.eval()

    weather = torch.zeros(1, len(PRODUCTION_WEATHER_FEATURES))
    weather[0, surface_pressure_index] = 95000.0
    for level in PRESSURE_LEVELS_HPA:
        z_index = PRODUCTION_WEATHER_FEATURES.index(
            f"geopotential_height_{level}hpa_m"
        )
        weather[0, z_index] = 1500.0

    captured: list[torch.Tensor] = []
    assert model.weather_profile_encoder is not None
    hook = model.weather_profile_encoder.register_forward_pre_hook(
        lambda _module, args: captured.append(args[0].detach().clone())
    )
    features = {
        "weather": {key: weather.clone() for key in model.time_keys},
        "site": torch.tensor([[50.0, 14.0, 500.0]]),
        "site_id": torch.tensor([0]),
        "date": torch.tensor([[0.0, 2026.0, 0.1, 0.9]]),
    }
    assert model(features).shape == (1, 11)
    hook.remove()

    assert len(captured) == 3
    profile = captured[0]
    assert profile.shape == (1, 6, 13)
    expected_valid = torch.tensor(
        [[0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]]
    )
    torch.testing.assert_close(profile[:, 5, :], expected_valid)
    torch.testing.assert_close(profile[:, 4, :2], torch.zeros(1, 2))
    torch.testing.assert_close(profile[:, 4, 2:], torch.full((1, 11), 1000.0))


def test_agl_scaling_is_fit_on_raw_noon_height_minus_site_altitude() -> None:
    frame = pd.DataFrame({"altitude": [100.0, 200.0, 300.0]})
    for level in PRESSURE_LEVELS_HPA:
        frame[f"geopotential_height_{level}hpa_m_12"] = [
            100.0 + level,
            210.0 + level,
            320.0 + level,
        ]

    features = XCFeatureContract(weather_features=PRODUCTION_WEATHER_FEATURES)
    means, stds, surface_pressure_index, site_altitude_index = _profile_agl_scaling(
        frame, features
    )

    assert means[0] == pytest.approx(1010.0)
    assert means[-1] == pytest.approx(510.0)
    assert stds == pytest.approx([10.0] * 13)
    assert surface_pressure_index == PRODUCTION_WEATHER_FEATURES.index("pressure_sfc_pa")
    assert site_altitude_index == 2


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


def test_agl_candidate_changes_only_the_profile_representation() -> None:
    vertical = load_config(CANDIDATE)
    agl = load_config(AGL_CANDIDATE)

    assert agl["task"] == vertical["task"]
    assert agl["data"] == vertical["data"]
    assert agl["evaluation"] == vertical["evaluation"]
    assert agl["tracking"] == vertical["tracking"]
    assert _without(agl["artifact"], "output_dir") == _without(
        vertical["artifact"], "output_dir"
    )
    assert _without(
        agl["model"], "name", "weather_profile_use_agl_mask"
    ) == _without(vertical["model"], "name")
    assert agl["model"]["weather_profile_use_agl_mask"] is True
