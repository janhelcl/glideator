from typing import Iterable, List

import numpy as np


def graded_relevance(q_bucket: int, nb_bucket: int) -> int:
    # rel=2: same bucket; rel=1: adjacent bucket; rel=0 otherwise
    if nb_bucket == q_bucket:
        return 2
    if abs(int(nb_bucket) - int(q_bucket)) == 1:
        return 1
    return 0


def dcg(rels: Iterable[float]) -> float:
    # rels is a list/array of graded relevance at ranks [1..k]
    rels = np.array(list(rels), dtype=float)
    if len(rels) == 0:
        return 0.0
    discounts = 1.0 / np.log2(np.arange(2, len(rels) + 2))
    return float(np.sum((2 ** rels - 1) * discounts))


def ndcg_at_k(rels: List[float], k: int) -> float:
    rels_k = rels[:k]
    ideal = sorted(rels_k, reverse=True)
    denom = dcg(ideal)
    return dcg(rels_k) / denom if denom > 0 else 0.0


def mrr(rels: List[float]) -> float:
    # rel>0 counts as "relevant"
    for i, r in enumerate(rels, start=1):
        if r > 0:
            return 1.0 / i
    return 0.0


def hit_at_k(rels: List[float], k: int) -> float:
    return 1.0 if any(r > 0 for r in rels[:k]) else 0.0


