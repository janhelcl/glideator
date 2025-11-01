from typing import Dict, List, Any, Tuple

import numpy as np
import pandas as pd

from .metrics import graded_relevance, ndcg_at_k, hit_at_k, mrr


def evaluate(
    val_df: pd.DataFrame,
    feat_cols: List[str],
    site_indices: Dict[Any, Dict[str, Any]],
    k: int = 10,
    site_col: str = "site_id",
    label_col: str = "max_points",
) -> Tuple[Dict[str, Any], pd.DataFrame]:
    ndcgs = []
    hits = []
    mrrs = []
    site_stats = []

    # Prepare normalized val vectors the same way (cosine)
    for site_id, g in val_df.groupby(site_col, sort=False):
        if site_id not in site_indices:
            continue  # site has no train history
        model = site_indices[site_id]
        X = g[feat_cols].to_numpy(dtype=np.float32, copy=False)
        norms = np.linalg.norm(X, axis=1, keepdims=True) + 1e-12
        Xn = X / norms

        # Query against train-only neighbors within the same site
        dists, idxs = model["nn"].kneighbors(
            Xn, n_neighbors=min(k, len(model["Xn"])), return_distance=True
        )

        # Compute graded relevance lists
        for row_i in range(len(g)):
            q_label = int(g.iloc[row_i][label_col])
            nb_idx = idxs[row_i]
            nb_labels = [int(model["labels"][j]) for j in nb_idx]
            rels = [graded_relevance(q_label, nb) for nb in nb_labels]

            ndcgs.append(ndcg_at_k(rels, k=len(rels)))
            hits.append(hit_at_k(rels, k=min(5, len(rels))))
            mrrs.append(mrr(rels))

        site_stats.append({
            "site_id": site_id,
            "n_queries": len(g),
            "mean_ndcg@10": float(np.mean(ndcgs[-len(g):])) if len(g) else np.nan,
            "mean_hit@5": float(np.mean(hits[-len(g):])) if len(g) else np.nan,
            "mean_mrr": float(np.mean(mrrs[-len(g):])) if len(g) else np.nan,
        })

    macro_stats = {
        "macro_ndcg@10": float(np.mean(ndcgs)) if ndcgs else np.nan,
        "macro_hit@5": float(np.mean(hits)) if hits else np.nan,
        "macro_mrr": float(np.mean(mrrs)) if mrrs else np.nan,
        "n_queries_total": int(len(ndcgs)),
    }
    return macro_stats, pd.DataFrame(site_stats)


def inspect_neighbors(
    site_id: Any,
    query_date: Any,
    val_df: pd.DataFrame,
    feat_cols: List[str],
    site_indices: Dict[Any, Dict[str, Any]],
    k: int = 5,
    top_m_deltas: int = 8,
    site_col: str = "site_id",
    date_col: str = "date",
    label_col: str = "max_points",
) -> Dict[str, Any]:
    qdf = val_df[(val_df[site_col] == site_id) & (val_df[date_col] == pd.Timestamp(query_date))]
    if qdf.empty:
        raise ValueError("Query day not found in validation set for this site.")

    model = site_indices.get(site_id)
    if model is None:
        raise ValueError("No train index for this site.")

    x = qdf.iloc[0][feat_cols].to_numpy(dtype=np.float32)
    x_n = x / (np.linalg.norm(x) + 1e-12)

    nnb = min(k, len(model["Xn"]))
    if nnb == 0:
        raise ValueError("This site has no train neighbors.")

    dists, idxs = model["nn"].kneighbors(x_n.reshape(1, -1), n_neighbors=nnb, return_distance=True)
    idxs, dists = idxs[0], dists[0]

    q_label = int(qdf.iloc[0][label_col])
    neighbors = []
    for r, (j, d) in enumerate(zip(idxs, dists), start=1):
        dte = pd.Timestamp(model["dates"][j]).date()
        neighbors.append({
            "rank": r,
            "date": dte,
            "distance": float(d),
            "label": int(model["labels"][j]),
        })

    # Feature deltas vs nearest neighbor
    j0 = idxs[0]
    nb_feat = model["features"][j0]
    deltas = (x - nb_feat)
    top_n = min(top_m_deltas, len(feat_cols))
    feat_imp_df = (pd.DataFrame({"feature": feat_cols, "delta": deltas, "abs_delta": np.abs(deltas)})
                     .sort_values("abs_delta", ascending=False)
                     .head(top_n))

    return {
        "query": {
            "site_id": site_id,
            "query_date": pd.Timestamp(query_date).date(),
            "label": q_label,
        },
        "neighbors": neighbors,
        "top_feature_deltas": feat_imp_df[["feature", "delta"]],
    }


