from __future__ import annotations

import math

import pandas as pd
import torch

from glideator_ml.xc.model import (
    CrossNet,
    ExpandedGlideatorNet,
    OrdinalHead,
    StandardScalerLayer,
)
from glideator_ml.xc.objective import xc_loss
from glideator_ml.xc.preprocessing import (
    DATE_FEATURES,
    TARGET_NAMES,
    XC_THRESHOLDS,
    add_date_features,
    add_targets,
    weather_features_by_time,
)


def _scaler(names: list[str]) -> StandardScalerLayer:
    return StandardScalerLayer(
        {name: {"mean": 0.0, "std": 1.0} for name in names}
    )


def test_crossnet_keeps_legacy_state_dict_and_equation() -> None:
    cross = CrossNet(in_features=2, num_layers=1)
    assert set(cross.state_dict()) == {"kernels.0", "bias.0"}
    assert cross.state_dict()["kernels.0"].shape == (2, 2)
    assert cross.state_dict()["bias.0"].shape == (2, 1)

    with torch.no_grad():
        cross.kernels[0].copy_(torch.tensor([[1.0, 2.0], [3.0, 4.0]]))
        cross.bias[0].copy_(torch.tensor([[0.5], [-0.5]]))

    inputs = torch.tensor([[2.0, 3.0]])
    kernel_product = torch.tensor([[8.0, 18.0]])
    expected = inputs * (kernel_product + torch.tensor([[0.5, -0.5]])) + inputs
    torch.testing.assert_close(cross(inputs), expected)


def test_migrated_model_preserves_production_module_contract() -> None:
    model = ExpandedGlideatorNet(
        weather_scaler=_scaler(["w1", "w2"]),
        site_scaler=_scaler(["s1", "s2", "s3"]),
        num_launches=5,
        num_targets=11,
        deep_hidden_units=(8, 4),
        cross_layers=2,
        site_embedding_dim=3,
    )

    state_keys = set(model.state_dict())
    assert "weather_scaler.means" in state_keys
    assert "site_scaler.stds" in state_keys
    assert "launch_embedding.weight" in state_keys
    assert "cross_net.kernels.0" in state_keys
    assert "cross_net.bias.1" in state_keys
    assert "prediction_head.output_layers.10.weight" in state_keys

    features = {
        "weather": {
            "9": torch.randn(4, 2),
            "12": torch.randn(4, 2),
            "15": torch.randn(4, 2),
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
    output = model(features)
    assert output.shape == (4, 11)
    assert torch.all((output >= 0.0) & (output <= 1.0))


def test_ordinal_head_is_monotonic_by_construction() -> None:
    head = OrdinalHead(input_dim=3, num_targets=11)
    predictions = head(torch.randn(16, 3))
    assert predictions.shape == (16, 11)
    assert torch.all(predictions[:, 1:] <= predictions[:, :-1])


def test_target_contract_uses_strict_thresholds() -> None:
    frame = pd.DataFrame({"max_points": [0.0, 10.0, 10.1, 100.0, 100.1]})
    result = add_targets(frame)

    assert XC_THRESHOLDS == tuple(range(0, 101, 10))
    assert TARGET_NAMES == tuple(f"XC{value}" for value in XC_THRESHOLDS)
    assert result["XC0"].tolist() == [0, 1, 1, 1, 1]
    assert result["XC10"].tolist() == [0, 0, 1, 1, 1]
    assert result["XC100"].tolist() == [0, 0, 0, 0, 1]
    assert "XC0" not in frame.columns


def test_date_feature_contract_matches_legacy_behavior() -> None:
    frame = pd.DataFrame(
        {"date": pd.to_datetime(["2026-09-04", "2026-09-05", "2026-01-01"])}
    )
    result = add_date_features(frame)

    assert DATE_FEATURES == (
        "weekend",
        "year",
        "day_of_year_sin",
        "day_of_year_cos",
    )
    assert result["weekend"].tolist() == [0, 1, 0]
    assert result["year"].tolist() == [2026, 2026, 2026]

    first_day_angle = 2 * math.pi / 365.25
    assert math.isclose(result.loc[2, "day_of_year_sin"], math.sin(first_day_angle))
    assert math.isclose(result.loc[2, "day_of_year_cos"], math.cos(first_day_angle))
    assert "weekend" not in frame.columns


def test_weather_columns_keep_production_suffix_split() -> None:
    features = ["tmp9", "wind12", "cape15", "level_925_9", "other"]
    split = weather_features_by_time(features)
    assert split == {
        9: ["tmp9", "level_925_9"],
        12: ["wind12"],
        15: ["cape15"],
    }


def test_xc_loss_matches_legacy_target_sum_and_monotonicity_penalty() -> None:
    predictions = torch.tensor(
        [[0.8, 0.6, 0.7], [0.4, 0.5, 0.2]], dtype=torch.float32
    )
    targets = torch.tensor(
        [[1.0, 1.0, 0.0], [0.0, 0.0, 0.0]], dtype=torch.float32
    )

    result = xc_loss(predictions, targets, monotonicity_lambda=2.0)

    criterion = torch.nn.BCELoss()
    expected_prediction = sum(
        criterion(predictions[:, index], targets[:, index])
        for index in range(predictions.shape[1])
    )
    expected_monotonicity = (
        torch.relu(predictions[:, 1] - predictions[:, 0]).mean()
        + torch.relu(predictions[:, 2] - predictions[:, 1]).mean()
    )

    torch.testing.assert_close(result.prediction, expected_prediction)
    torch.testing.assert_close(result.monotonicity, expected_monotonicity)
    torch.testing.assert_close(
        result.total, expected_prediction + 2.0 * expected_monotonicity
    )
