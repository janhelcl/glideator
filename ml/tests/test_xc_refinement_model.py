from __future__ import annotations

import pytest
import torch
from torch import nn

from glideator_ml.xc.model import ExpandedGlideatorNet, StandardScalerLayer


def _scaler(names: list[str]) -> StandardScalerLayer:
    return StandardScalerLayer(
        {name: {"mean": 0.0, "std": 1.0} for name in names}
    )


def _model(**kwargs: object) -> ExpandedGlideatorNet:
    return ExpandedGlideatorNet(
        weather_scaler=_scaler(["w1", "w2"]),
        site_scaler=_scaler(["s1", "s2", "s3"]),
        num_launches=5,
        num_targets=11,
        deep_hidden_units=(8, 4),
        cross_layers=0,
        site_embedding_dim=3,
        parallel_deep_hidden_units=(6, 5),
        **kwargs,
    )


def _features() -> dict[str, object]:
    return {
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


def _first_linear(module: nn.Sequential) -> nn.Linear:
    layer = module[0]
    assert isinstance(layer, nn.Linear)
    return layer


def test_no_raw_skip_removes_time_input_from_fusion() -> None:
    baseline = _model(include_time_input_branch=True)
    no_raw_skip = _model(include_time_input_branch=False)

    baseline_fusion = _first_linear(baseline.deep_net)
    no_skip_fusion = _first_linear(no_raw_skip.deep_net)

    # Per time slice: 12 raw inputs + 5 encoder outputs versus encoder only.
    assert baseline_fusion.in_features == 3 * (12 + 5)
    assert no_skip_fusion.in_features == 3 * 5
    assert not hasattr(no_raw_skip, "cross_net")
    assert no_raw_skip(_features()).shape == (4, 11)


def test_time_specific_encoder_uses_independent_towers() -> None:
    shared = _model(share_parallel_deep_net=True)
    time_specific = _model(share_parallel_deep_net=False)

    assert shared.parallel_deep_net is not None
    assert not hasattr(shared, "parallel_deep_nets")
    assert time_specific.parallel_deep_net is None
    assert set(time_specific.parallel_deep_nets) == {"9", "12", "15"}

    weight_9 = _first_linear(time_specific.parallel_deep_nets["9"]).weight
    weight_12 = _first_linear(time_specific.parallel_deep_nets["12"]).weight
    assert weight_9.data_ptr() != weight_12.data_ptr()
    assert time_specific(_features()).shape == (4, 11)


def test_disabling_input_branch_requires_zero_cross_layers() -> None:
    with pytest.raises(ValueError, match="cross_layers must be 0"):
        ExpandedGlideatorNet(
            weather_scaler=_scaler(["w1", "w2"]),
            site_scaler=_scaler(["s1", "s2", "s3"]),
            num_launches=5,
            cross_layers=1,
            parallel_deep_hidden_units=(6, 5),
            include_time_input_branch=False,
        )
