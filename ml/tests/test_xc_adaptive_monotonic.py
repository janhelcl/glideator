from __future__ import annotations

import torch

from glideator_ml.xc.model import AdaptiveMonotonicHead


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
