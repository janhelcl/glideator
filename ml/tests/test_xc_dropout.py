from __future__ import annotations

import pytest
import torch

from glideator_ml.xc.model import ExpandedGlideatorNet, StandardScalerLayer


def _scaler(names: list[str]) -> StandardScalerLayer:
    return StandardScalerLayer(
        {name: {"mean": 0.0, "std": 1.0} for name in names}
    )


def _model(dropout: float) -> ExpandedGlideatorNet:
    return ExpandedGlideatorNet(
        weather_scaler=_scaler(["w1", "w2"]),
        site_scaler=_scaler(["s1", "s2", "s3"]),
        num_launches=5,
        num_targets=11,
        deep_hidden_units=(8, 4),
        cross_layers=0,
        site_embedding_dim=3,
        parallel_deep_hidden_units=(8, 4),
        dropout=dropout,
    )


def test_dropout_is_opt_in_without_changing_parameter_count() -> None:
    baseline = _model(0.0)
    regularized = _model(0.1)

    assert not any(
        isinstance(module, torch.nn.Dropout) for module in baseline.modules()
    )
    dropouts = [
        module
        for module in regularized.modules()
        if isinstance(module, torch.nn.Dropout)
    ]
    assert len(dropouts) == 4
    assert all(module.p == pytest.approx(0.1) for module in dropouts)

    assert "parallel_deep_net.2.weight" in baseline.state_dict()
    assert "deep_net.2.weight" in baseline.state_dict()
    assert sum(parameter.numel() for parameter in baseline.parameters()) == sum(
        parameter.numel() for parameter in regularized.parameters()
    )


@pytest.mark.parametrize("dropout", [-0.1, 1.0])
def test_dropout_rejects_invalid_probability(dropout: float) -> None:
    with pytest.raises(ValueError, match="dropout must satisfy"):
        _model(dropout)
