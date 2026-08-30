from __future__ import annotations

import math
from collections import Counter

import numpy as np
import pandas as pd

from .artifact import S2SArtifact, recommend


def evaluate(
    artifact: S2SArtifact,
    events: list[tuple[str, tuple[int, ...], int]],
    train_visits: pd.DataFrame,
    *,
    ks: list[int],
) -> dict[str, float | int]:
    if not ks or min(ks) <= 0:
        raise ValueError("evaluation.ks must contain positive integers")

    ks = sorted(set(int(k) for k in ks))
    max_k = max(ks)
    popularity = Counter(train_visits["site_id"].astype(int).tolist())
    catalog_size = len(artifact.idx_to_site)

    eligible = 0
    known_source = 0
    cold_start_targets = 0
    ranks: list[int | None] = []
    recommendations: list[list[int]] = []

    for _, source_ids, target_id in events:
        if any(site_id in artifact.site_to_idx for site_id in source_ids):
            known_source += 1
        if target_id not in artifact.site_to_idx:
            cold_start_targets += 1
            continue

        ranked = [site_id for site_id, _ in recommend(artifact, source_ids, top_k=max_k)]
        if not ranked:
            continue

        eligible += 1
        recommendations.append(ranked)
        try:
            rank = ranked.index(target_id) + 1
        except ValueError:
            rank = None
        ranks.append(rank)

    metrics: dict[str, float | int] = {
        "events": len(events),
        "eligible_events": eligible,
        "catalog_size": catalog_size,
        "cold_start_target_rate": (
            cold_start_targets / len(events) if events else 0.0
        ),
        "known_source_rate": known_source / len(events) if events else 0.0,
    }

    for k in ks:
        if eligible:
            hits = [rank is not None and rank <= k for rank in ranks]
            reciprocal = [
                1.0 / rank if rank is not None and rank <= k else 0.0
                for rank in ranks
            ]
            ndcg = [
                1.0 / math.log2(rank + 1) if rank is not None and rank <= k else 0.0
                for rank in ranks
            ]
            metrics[f"hit_rate_at_{k}"] = float(np.mean(hits))
            metrics[f"mrr_at_{k}"] = float(np.mean(reciprocal))
            metrics[f"ndcg_at_{k}"] = float(np.mean(ndcg))
        else:
            metrics[f"hit_rate_at_{k}"] = 0.0
            metrics[f"mrr_at_{k}"] = 0.0
            metrics[f"ndcg_at_{k}"] = 0.0

        recommended = [site for row in recommendations for site in row[:k]]
        metrics[f"coverage_at_{k}"] = (
            len(set(recommended)) / catalog_size if catalog_size else 0.0
        )
        metrics[f"avg_log_popularity_at_{k}"] = (
            float(np.mean([math.log1p(popularity[site]) for site in recommended]))
            if recommended
            else 0.0
        )

    return metrics
