from typing import Dict, List, Any

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors


def build_site_indices(train_df: pd.DataFrame, feat_cols: List[str], site_col: str = "site_id", date_col: str = "date", label_col: str = "max_points") -> Dict[Any, Dict[str, Any]]:
    # Pre-slice arrays per-site for fast lookup
    by_site: Dict[Any, Dict[str, Any]] = {}
    for site_id, g in train_df.groupby(site_col, sort=False):
        X = g[feat_cols].to_numpy(dtype=np.float32, copy=False)
        # Cosine distance → normalize vectors to unit length (optional but helps)
        norms = np.linalg.norm(X, axis=1, keepdims=True) + 1e-12
        Xn = X / norms
        nn = NearestNeighbors(metric="cosine", algorithm="brute")
        nn.fit(Xn)
        by_site[site_id] = {
            "nn": nn,
            "Xn": Xn,
            "dates": g[date_col].to_numpy(),
            "labels": g[label_col].to_numpy(),
            "features": X,  # keep unnormalized for qualitative deltas
        }
    return by_site


