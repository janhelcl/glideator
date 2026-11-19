from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score

from .preprocessing import TARGET_NAMES


def evaluate_predictions(
    targets: np.ndarray,
    probabilities: np.ndarray,
) -> dict[str, float]:
    if targets.shape != probabilities.shape:
        raise ValueError(
            f"XC targets/probabilities shape mismatch: {targets.shape} vs {probabilities.shape}"
        )
    if targets.ndim != 2 or targets.shape[1] != len(TARGET_NAMES):
        raise ValueError("XC evaluation expects rank-2 arrays with eleven targets")

    clipped = np.clip(probabilities.astype(float), 1e-7, 1.0 - 1e-7)
    truth = targets.astype(float)
    bce = -(truth * np.log(clipped) + (1.0 - truth) * np.log(1.0 - clipped)).mean(axis=0)
    brier = np.square(clipped - truth).mean(axis=0)

    metrics: dict[str, float] = {
        "validation_loss": float(bce.sum()),
        "bce_macro": float(bce.mean()),
        "brier_macro": float(brier.mean()),
        "monotonic_violation_rate": float(
            np.mean(probabilities[:, 1:] > probabilities[:, :-1])
        ),
        "monotonic_violation_mean": float(
            np.maximum(probabilities[:, 1:] - probabilities[:, :-1], 0.0).mean()
        ),
    }

    auc_values: list[float] = []
    for index, target_name in enumerate(TARGET_NAMES):
        metrics[f"bce_{target_name}"] = float(bce[index])
        metrics[f"brier_{target_name}"] = float(brier[index])
        if np.unique(truth[:, index]).size >= 2:
            auc = float(roc_auc_score(truth[:, index], probabilities[:, index]))
            metrics[f"roc_auc_{target_name}"] = auc
            auc_values.append(auc)
    if auc_values:
        metrics["roc_auc_macro"] = float(np.mean(auc_values))
    return metrics
