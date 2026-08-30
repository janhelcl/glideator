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
    scorer: dict[str, Any] | None = None

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

        if self.scorer is not None:
            self._validate_scorer()

    def _validate_scorer(self) -> None:
        if self.scorer is None:
            return
        scorer_type = self.scorer.get("type")
        if scorer_type == "asymmetric":
            source_matrix = np.asarray(self.scorer["source_matrix"])
            if source_matrix.shape != self.matrix.shape:
                raise ValueError(
                    "Asymmetric source matrix must match target embedding shape"
                )
            if not np.isfinite(source_matrix).all():
                raise ValueError(
                    "Asymmetric source matrix contains non-finite values"
                )
            return
        if scorer_type != "deepsets":
            raise ValueError(f"Unsupported S2S scorer type: {scorer_type!r}")

        pooling = self.scorer.get("pooling")
        if pooling not in {"mean", "sum"}:
            raise ValueError("DeepSets scorer pooling must be 'mean' or 'sum'")

        dimension = self.matrix.shape[1]
        phi_w1 = np.asarray(self.scorer["phi_w1"])
        phi_b1 = np.asarray(self.scorer["phi_b1"])
        phi_w2 = np.asarray(self.scorer["phi_w2"])
        phi_b2 = np.asarray(self.scorer["phi_b2"])
        rho_w1 = np.asarray(self.scorer["rho_w1"])
        rho_b1 = np.asarray(self.scorer["rho_b1"])
        rho_w2 = np.asarray(self.scorer["rho_w2"])
        rho_b2 = np.asarray(self.scorer["rho_b2"])

        phi_hidden = phi_w1.shape[0]
        rho_hidden = rho_w1.shape[0]
        expected_shapes = {
            "phi_w1": (phi_hidden, dimension),
            "phi_b1": (phi_hidden,),
            "phi_w2": (dimension, phi_hidden),
            "phi_b2": (dimension,),
            "rho_w1": (rho_hidden, dimension),
            "rho_b1": (rho_hidden,),
            "rho_w2": (dimension, rho_hidden),
            "rho_b2": (dimension,),
        }
        arrays = {
            "phi_w1": phi_w1,
            "phi_b1": phi_b1,
            "phi_w2": phi_w2,
            "phi_b2": phi_b2,
            "rho_w1": rho_w1,
            "rho_b1": rho_b1,
            "rho_w2": rho_w2,
            "rho_b2": rho_b2,
        }
        for name, array in arrays.items():
            if array.shape != expected_shapes[name]:
                raise ValueError(
                    f"DeepSets scorer {name} has shape {array.shape}, "
                    f"expected {expected_shapes[name]}"
                )
            if not np.isfinite(array).all():
                raise ValueError(f"DeepSets scorer {name} contains non-finite values")

    def to_payload(self) -> dict[str, Any]:
        self.validate()
        # The first three keys intentionally preserve the current backend contract.
        payload = {
            "site_to_idx": self.site_to_idx,
            "idx_to_site": self.idx_to_site,
            "matrix": self.matrix,
            "metadata": self.metadata,
        }
        if self.scorer is not None:
            payload["scorer"] = self.scorer
        return payload

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
        raw_scorer = payload.get("scorer")
        artifact = cls(
            site_to_idx={int(k): int(v) for k, v in payload["site_to_idx"].items()},
            idx_to_site=[int(site_id) for site_id in payload["idx_to_site"]],
            matrix=np.asarray(payload["matrix"], dtype=np.float32),
            metadata=dict(payload.get("metadata", {})),
            scorer=dict(raw_scorer) if raw_scorer is not None else None,
        )
        artifact.validate()
        return artifact


def _deepsets_query(artifact: S2SArtifact, idxs: list[int]) -> np.ndarray:
    scorer = artifact.scorer
    if scorer is None:
        raise ValueError("DeepSets query requested without scorer state")

    items = artifact.matrix[idxs]
    phi = np.maximum(
        items @ np.asarray(scorer["phi_w1"]).T + np.asarray(scorer["phi_b1"]),
        0.0,
    )
    phi = phi @ np.asarray(scorer["phi_w2"]).T + np.asarray(scorer["phi_b2"])
    if scorer["pooling"] == "mean":
        pooled = phi.mean(axis=0)
    else:
        pooled = phi.sum(axis=0)

    hidden = np.maximum(
        pooled @ np.asarray(scorer["rho_w1"]).T + np.asarray(scorer["rho_b1"]),
        0.0,
    )
    return hidden @ np.asarray(scorer["rho_w2"]).T + np.asarray(scorer["rho_b2"])


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

    if artifact.scorer is None:
        query = artifact.matrix[idxs].sum(axis=0)
    elif artifact.scorer.get("type") == "asymmetric":
        query = np.asarray(artifact.scorer["source_matrix"])[idxs].sum(axis=0)
    elif artifact.scorer.get("type") == "deepsets":
        query = _deepsets_query(artifact, idxs)
    else:
        raise ValueError(
            f"Unsupported S2S scorer type: {artifact.scorer.get('type')!r}"
        )

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
