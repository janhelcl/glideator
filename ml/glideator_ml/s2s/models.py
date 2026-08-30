from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.utils.extmath import randomized_svd

from .artifact import S2SArtifact


def fit_svd(
    train_visits: pd.DataFrame,
    *,
    n_factors: int,
    sigma_power: float,
    seed: int,
    metadata: dict[str, Any] | None = None,
) -> S2SArtifact:
    if train_visits.empty:
        raise ValueError("Cannot fit S2S SVD on an empty training set")

    pilots = sorted(train_visits["pilot"].astype(str).unique())
    sites = sorted(int(site) for site in train_visits["site_id"].unique())
    pilot_to_idx = {pilot: index for index, pilot in enumerate(pilots)}
    site_to_idx = {site_id: index for index, site_id in enumerate(sites)}

    rows = train_visits["pilot"].astype(str).map(pilot_to_idx).to_numpy()
    cols = train_visits["site_id"].astype(int).map(site_to_idx).to_numpy()
    values = np.ones(len(train_visits), dtype=np.float32)
    matrix = sparse.csr_matrix(
        (values, (rows, cols)),
        shape=(len(pilots), len(sites)),
        dtype=np.float32,
    )
    matrix.data[:] = 1.0

    max_rank = min(matrix.shape)
    if max_rank < 2:
        raise ValueError("S2S SVD needs at least two pilots and two sites")
    components = min(int(n_factors), max_rank - 1)
    if components < 1:
        raise ValueError("n_factors must be positive")

    _, singular_values, vt = randomized_svd(
        matrix,
        n_components=components,
        random_state=seed,
    )
    embeddings = vt.T * np.power(singular_values, float(sigma_power))
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = np.divide(
        embeddings,
        norms,
        out=np.zeros_like(embeddings),
        where=norms > 0,
    ).astype(np.float32)

    artifact_metadata = {
        "model_type": "svd",
        "n_factors_requested": int(n_factors),
        "n_factors_fitted": int(components),
        "sigma_power": float(sigma_power),
        "seed": int(seed),
        "train_pilots": len(pilots),
        "catalog_size": len(sites),
        "train_interactions": int(matrix.nnz),
        **(metadata or {}),
    }
    artifact = S2SArtifact(
        site_to_idx=site_to_idx,
        idx_to_site=sites,
        matrix=embeddings,
        metadata=artifact_metadata,
    )
    artifact.validate()
    return artifact
