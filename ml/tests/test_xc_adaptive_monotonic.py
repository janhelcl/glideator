from __future__ import annotations

from pathlib import Path

import torch

from glideator_ml.config import load_config
from glideator_ml.xc.model import AdaptiveMonotonicHead


CONFIG_DIR = Path(__file__).parents[1] / "configs" / "xc" / "architecture"


def test_adaptive_monotonic_head_is_monotonic_by_construction() -> None:
    head = AdaptiveMonotonicHead(input_dim=4, num_targets=11)
    predictions = head(torch.randn(32, 4))

    assert predictions.shape == (32, 11)
    assert torch.all((predictions >= 0.0) & (predictions <= 1.0))
    assert torch.all(predictions[:, 1:] <= predictions[:, :-1])


def test_adaptive_monotonic_head_can_condition_threshold_gaps_on_features() -> None:
    head = AdaptiveMonotonicHead(input_dim=2, num_targets=3)
    with torch.no_grad():
        head.base_logit.weight.zero_()
        head.base_logit.bias.zero_()
        head.gap_logits.weight.zero_()
        head.gap_logits.bias.fill_(-1.0)
        head.gap_logits.weight[0, 0] = 2.0

    low = head(torch.tensor([[0.0, 0.0]]))
    high = head(torch.tensor([[1.0, 0.0]]))

    # XC0 is unchanged because only the first threshold gap depends on x[0].
    torch.testing.assert_close(low[:, 0], high[:, 0])
    # Harder thresholds move because their cumulative gap is feature-conditioned.
    assert high[0, 1] < low[0, 1]
    assert high[0, 2] < low[0, 2]
    assert torch.all(high[:, 1:] <= high[:, :-1])


def test_adaptive_monotonic_experiment_uses_no_cross_baseline() -> None:
    baseline = load_config(CONFIG_DIR / "no_cross.yaml")
    adaptive = load_config(CONFIG_DIR / "adaptive_monotonic.yaml")

    invariant_data = (
        "start_date",
        "max_site_id",
        "split_strategy",
        "train_end",
        "eval_start",
        "eval_end",
        "require_known_eval_sites",
        "require_eval_boundary_coverage",
        "site_features",
    )
    invariant_model = (
        "seed",
        "deterministic",
        "device",
        "validation_start",
        "num_launches",
        "site_embedding_dim",
        "deep_hidden_units",
        "cross_layers",
        "parallel_deep_hidden_units",
        "share_cross_net",
        "batch_size",
        "num_workers",
        "learning_rate",
        "lr_decay",
        "epochs",
        "patience",
        "l1_lambda",
        "l2_lambda",
    )

    for key in invariant_data:
        assert adaptive["data"][key] == baseline["data"][key], key
    for key in invariant_model:
        assert adaptive["model"][key] == baseline["model"][key], key

    assert adaptive["model"]["prediction_head_type"] == "adaptive_monotonic"
    assert adaptive["model"]["monotonicity_lambda"] == 0.0
    assert baseline["model"]["prediction_head_type"] == "multilabel"
    assert adaptive["evaluation"]["benchmark_id"] == baseline["evaluation"]["benchmark_id"]
    assert adaptive["artifact"]["export_onnx"] is False
