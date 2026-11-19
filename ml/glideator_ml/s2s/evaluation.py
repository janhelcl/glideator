from __future__ import annotations

import math
from collections import Counter
from typing import Any

import numpy as np
import pandas as pd

from .artifact import S2SArtifact, recommend


def _history_bucket(history_length: int) -> str:
    if history_length <= 1:
        return "history_1"
    if history_length <= 3:
        return "history_2_3"
    return "history_4_plus"


def _head_sites(popularity: Counter[int]) -> set[int]:
    if not popularity:
        return set()
    ranked = sorted(popularity, key=lambda site_id: (-popularity[site_id], site_id))
    head_size = max(1, math.ceil(len(ranked) * 0.20))
    return set(ranked[:head_size])


def _ranking_metrics(
    outcomes: list[dict[str, Any]],
    *,
    ks: list[int],
    prefix: str = "",
) -> dict[str, float | int]:
    eligible = [row for row in outcomes if row["eligible"]]
    metrics: dict[str, float | int] = {
        f"{prefix}events": len(outcomes),
        f"{prefix}eligible_events": len(eligible),
    }
    for k in ks:
        eligible_hits = [
            row["rank"] is not None and row["rank"] <= k for row in eligible
        ]
        reciprocal = [
            1.0 / row["rank"]
            if row["rank"] is not None and row["rank"] <= k
            else 0.0
            for row in eligible
        ]
        ndcg = [
            1.0 / math.log2(row["rank"] + 1)
            if row["rank"] is not None and row["rank"] <= k
            else 0.0
            for row in eligible
        ]
        all_hits = [
            row["rank"] is not None and row["rank"] <= k for row in outcomes
        ]
        metrics[f"{prefix}hit_rate_at_{k}"] = (
            float(np.mean(eligible_hits)) if eligible_hits else 0.0
        )
        metrics[f"{prefix}mrr_at_{k}"] = (
            float(np.mean(reciprocal)) if reciprocal else 0.0
        )
        metrics[f"{prefix}ndcg_at_{k}"] = float(np.mean(ndcg)) if ndcg else 0.0
        metrics[f"{prefix}end_to_end_hit_rate_at_{k}"] = (
            float(np.mean(all_hits)) if all_hits else 0.0
        )
    return metrics


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
    head_sites = _head_sites(popularity)
    catalog_size = len(artifact.idx_to_site)

    known_source = 0
    cold_start_targets = 0
    outcomes: list[dict[str, Any]] = []
    recommendations: list[list[int]] = []

    for _, source_ids, target_id in events:
        source_known = any(
            site_id in artifact.site_to_idx for site_id in source_ids
        )
        if source_known:
            known_source += 1

        target_known = target_id in artifact.site_to_idx
        if not target_known:
            cold_start_targets += 1
            target_bucket = "target_cold_start"
        elif target_id in head_sites:
            target_bucket = "target_head"
        else:
            target_bucket = "target_tail"

        ranked: list[int] = []
        if target_known:
            ranked = [
                site_id
                for site_id, _ in recommend(artifact, source_ids, top_k=max_k)
            ]

        eligible = bool(ranked)
        rank = None
        if eligible:
            recommendations.append(ranked)
            try:
                rank = ranked.index(target_id) + 1
            except ValueError:
                rank = None

        outcomes.append(
            {
                "rank": rank,
                "eligible": eligible,
                "history_bucket": _history_bucket(len(source_ids)),
                "target_bucket": target_bucket,
            }
        )

    metrics = _ranking_metrics(outcomes, ks=ks)
    metrics.update(
        {
            "catalog_size": catalog_size,
            "cold_start_target_rate": (
                cold_start_targets / len(events) if events else 0.0
            ),
            "known_source_rate": known_source / len(events) if events else 0.0,
        }
    )

    for k in ks:
        recommended = [site for row in recommendations for site in row[:k]]
        metrics[f"coverage_at_{k}"] = (
            len(set(recommended)) / catalog_size if catalog_size else 0.0
        )
        metrics[f"avg_log_popularity_at_{k}"] = (
            float(np.mean([math.log1p(popularity[site]) for site in recommended]))
            if recommended
            else 0.0
        )

    for bucket in ("history_1", "history_2_3", "history_4_plus"):
        subset = [row for row in outcomes if row["history_bucket"] == bucket]
        metrics.update(_ranking_metrics(subset, ks=ks, prefix=f"{bucket}_"))

    for bucket in ("target_head", "target_tail", "target_cold_start"):
        subset = [row for row in outcomes if row["target_bucket"] == bucket]
        metrics.update(_ranking_metrics(subset, ks=ks, prefix=f"{bucket}_"))

    return metrics
