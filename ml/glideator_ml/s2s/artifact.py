from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class S2SArtifact:
    site_to_idx: dict[int, int]
    idx_to_site: list[int]
    matrix: np.ndarray
    metadata: dict[str, Any]

    def validate(self) -> None:
        if self.matrix.ndim != 2:
            raise ValueError("S2S embedding matrix must be two-dimensional")
        if self.matrix.shape[0] != len(self.idx_to_site):
            raise ValueError("Embedding row count does not match idx_to_site")
        if set(self.site_to_idx) != set(self.idx_to_site):
            raise ValueError("site_to_idx and idx_to_site describe different catalogs")
        for index, site_id in enumerate(self.idx_to_site):
            if self.site_to_idx[site_id] != index:
                raise ValueError("S2S site index mappings are inconsistent")
        if not np.isfinite(self.matrix).all():
            raise ValueError("S2S embedding matrix contains non-finite values")

    def to_payload(self) -> dict[str, Any]:
        self.validate()
        # The first three keys intentionally preserve the current backend contract.
        return {
            "site_to_idx": self.site_to_idx,
            "idx_to_site": self.idx_to_site,
            "matrix": self.matrix,
            "metadata": self.metadata,
        }

    def save(self, path: str | Path) -> Path:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as handle:
            pickle.dump(self.to_payload(), handle, protocol=pickle.HIGHEST_PROTOCOL)
        return destination

    @classmethod
    def load(cls, path: str | Path) -> "S2SArtifact":
        with Path(path).open("rb") as handle:
            payload = pickle.load(handle)
        artifact = cls(
            site_to_idx={int(k): int(v) for k, v in payload["site_to_idx"].items()},
            idx_to_site=[int(site_id) for site_id in payload["idx_to_site"]],
            matrix=np.asarray(payload["matrix"], dtype=np.float32),
            metadata=dict(payload.get("metadata", {})),
        )
        artifact.validate()
        return artifact


def recommend(
    artifact: S2SArtifact,
    source_ids: tuple[int, ...] | list[int],
    *,
    top_k: int,
) -> list[tuple[int, float]]:
    idxs = [
        artifact.site_to_idx[site_id]
        for site_id in source_ids
        if site_id in artifact.site_to_idx
    ]
    if not idxs or top_k <= 0:
        return []

    query = artifact.matrix[idxs].sum(axis=0)
    norm = np.linalg.norm(query)
    if norm == 0.0:
        return []
    query = query / norm

    scores = artifact.matrix @ query
    scores = scores.copy()
    scores[idxs] = -np.inf
    candidate_count = scores.size - len(set(idxs))
    if candidate_count <= 0:
        return []

    k = min(top_k, candidate_count)
    top = np.argpartition(-scores, k - 1)[:k]
    top = top[np.argsort(-scores[top], kind="mergesort")]
    return [
        (int(artifact.idx_to_site[index]), float(scores[index]))
        for index in top
        if np.isfinite(scores[index])
    ]
