from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn


@dataclass(frozen=True)
class XCLoss:
    total: torch.Tensor
    prediction: torch.Tensor
    monotonicity: torch.Tensor


def xc_loss(
    predictions: torch.Tensor,
    targets: torch.Tensor,
    monotonicity_lambda: float = 0.0,
    criterion: nn.Module | None = None,
) -> XCLoss:
    """Compute the legacy XC objective with explicit loss components.

    Production training computes a mean BCE independently for every XC threshold and
    sums those values. The optional monotonicity penalty then sums adjacent violations
    where a harder threshold receives a higher probability than the preceding one.
    """

    if predictions.shape != targets.shape:
        raise ValueError(
            f"predictions and targets must have the same shape, got "
            f"{tuple(predictions.shape)} and {tuple(targets.shape)}"
        )
    if predictions.ndim != 2:
        raise ValueError("XC predictions and targets must be rank-2 tensors")

    criterion = criterion or nn.BCELoss()
    per_target_losses = [
        criterion(predictions[:, index], targets[:, index])
        for index in range(predictions.shape[1])
    ]
    prediction_loss = torch.stack(per_target_losses).sum()

    if predictions.shape[1] > 1:
        monotonicity_loss = torch.stack(
            [
                torch.relu(predictions[:, index] - predictions[:, index - 1]).mean()
                for index in range(1, predictions.shape[1])
            ]
        ).sum()
    else:
        monotonicity_loss = predictions.new_zeros(())

    total_loss = prediction_loss + monotonicity_lambda * monotonicity_loss
    return XCLoss(
        total=total_loss,
        prediction=prediction_loss,
        monotonicity=monotonicity_loss,
    )
