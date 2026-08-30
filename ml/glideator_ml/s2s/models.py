from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.utils.extmath import randomized_svd

from .artifact import S2SArtifact

logger = logging.getLogger(__name__)


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


def fit_contrastive(
    train_visits: pd.DataFrame,
    *,
    n_factors: int,
    epochs: int,
    learning_rate: float,
    weight_decay: float,
    temperature: float,
    batch_size: int,
    negative_samples: int,
    add_inbatch_negatives: bool,
    seed: int,
    device: str = "auto",
    metadata: dict[str, Any] | None = None,
) -> S2SArtifact:
    """Fit the contrastive architecture used by the production S2S model."""
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, Dataset
    except ImportError as exc:
        raise RuntimeError(
            "Contrastive S2S training requires the 'contrastive' extra"
        ) from exc

    if train_visits.empty:
        raise ValueError("Cannot fit contrastive S2S on an empty training set")

    torch.manual_seed(seed)
    np.random.seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    sites = sorted(int(site) for site in train_visits["site_id"].unique())
    site_to_idx = {site_id: index for index, site_id in enumerate(sites)}
    ordered = train_visits.sort_values(
        ["pilot", "visit_at", "site_id"], kind="mergesort"
    )
    episodes: list[tuple[np.ndarray, int]] = []
    for _, group in ordered.groupby("pilot", sort=True):
        indices = [site_to_idx[int(site)] for site in group["site_id"]]
        episodes.extend(
            (np.asarray(indices[:position], dtype=np.int64), indices[position])
            for position in range(1, len(indices))
        )
    if not episodes:
        raise ValueError("Contrastive S2S needs at least one training episode")

    popularity = np.zeros(len(sites), dtype=np.float64)
    for site_id, count in train_visits["site_id"].value_counts().items():
        popularity[site_to_idx[int(site_id)]] = float(count)

    class EpisodeDataset(Dataset):
        def __len__(self):
            return len(episodes)

        def __getitem__(self, index):
            return episodes[index]

    def collate(batch):
        histories, targets = zip(*batch)
        offsets = np.cumsum([0, *[len(history) for history in histories]])
        return (
            torch.as_tensor(np.concatenate(histories), dtype=torch.long),
            torch.as_tensor(offsets, dtype=torch.long),
            torch.as_tensor(targets, dtype=torch.long),
        )

    class DiscoveryModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.item_embeddings = nn.Embedding(len(sites), int(n_factors))
            self.history_embeddings = nn.EmbeddingBag(
                len(sites),
                int(n_factors),
                mode="sum",
                include_last_offset=True,
            )
            self.history_embeddings.weight = self.item_embeddings.weight
            nn.init.normal_(self.item_embeddings.weight, std=0.02)

        def forward(self, flat, offsets, targets, negatives):
            query = nn.functional.normalize(
                self.history_embeddings(flat, offsets), dim=1
            )
            positive = nn.functional.normalize(
                self.item_embeddings(targets), dim=1
            )
            negative = nn.functional.normalize(
                self.item_embeddings(negatives), dim=2
            )
            positive_logits = (query * positive).sum(dim=1, keepdim=True)
            negative_logits = torch.einsum("bd,bkd->bk", query, negative)
            if add_inbatch_negatives:
                inbatch = query @ positive.T
                inbatch = inbatch - torch.eye(
                    inbatch.size(0), device=inbatch.device
                ) * 1e9
                negative_logits = torch.cat([negative_logits, inbatch], dim=1)
            logits = torch.cat([positive_logits, negative_logits], dim=1)
            labels = torch.zeros(logits.size(0), dtype=torch.long, device=logits.device)
            return nn.functional.cross_entropy(logits / temperature, labels)

    resolved_device = (
        "cuda" if device == "auto" and torch.cuda.is_available() else device
    )
    if resolved_device == "auto":
        resolved_device = "cpu"
    model = DiscoveryModel().to(resolved_device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(learning_rate),
        weight_decay=float(weight_decay),
    )
    generator = torch.Generator().manual_seed(seed)
    loader = DataLoader(
        EpisodeDataset(),
        batch_size=int(batch_size),
        shuffle=True,
        collate_fn=collate,
        generator=generator,
        num_workers=0,
    )
    sampling_weights = torch.as_tensor(
        np.power(popularity + 1e-8, 0.75),
        dtype=torch.float32,
        device=resolved_device,
    )
    sampling_generator = torch.Generator(device=resolved_device).manual_seed(seed)
    final_loss = 0.0
    for epoch in range(1, int(epochs) + 1):
        model.train()
        total_loss = 0.0
        examples = 0
        for flat, offsets, targets in loader:
            flat = flat.to(resolved_device)
            offsets = offsets.to(resolved_device)
            targets = targets.to(resolved_device)
            weights = sampling_weights.expand(len(targets), -1).clone()
            row_indices = torch.repeat_interleave(
                torch.arange(len(targets), device=resolved_device),
                offsets[1:] - offsets[:-1],
            )
            weights[row_indices, flat] = 0
            weights[torch.arange(len(targets), device=resolved_device), targets] = 0
            negatives = torch.multinomial(
                weights,
                num_samples=int(negative_samples),
                replacement=False,
                generator=sampling_generator,
            )
            optimizer.zero_grad(set_to_none=True)
            loss = model(flat, offsets, targets, negatives)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += float(loss.detach()) * len(targets)
            examples += len(targets)
        final_loss = total_loss / examples
        logger.info(
            "Contrastive S2S epoch %d/%d loss=%.4f",
            epoch,
            epochs,
            final_loss,
        )

    model.eval()
    with torch.no_grad():
        embeddings = nn.functional.normalize(
            model.item_embeddings.weight, dim=1
        ).cpu().numpy().astype(np.float32)

    artifact = S2SArtifact(
        site_to_idx=site_to_idx,
        idx_to_site=sites,
        matrix=embeddings,
        metadata={
            "model_type": "contrastive",
            "n_factors": int(n_factors),
            "epochs": int(epochs),
            "learning_rate": float(learning_rate),
            "weight_decay": float(weight_decay),
            "temperature": float(temperature),
            "batch_size": int(batch_size),
            "negative_samples": int(negative_samples),
            "add_inbatch_negatives": bool(add_inbatch_negatives),
            "seed": int(seed),
            "device": resolved_device,
            "train_pilots": int(train_visits["pilot"].nunique()),
            "train_episodes": len(episodes),
            "catalog_size": len(sites),
            "final_loss": final_loss,
            **(metadata or {}),
        },
    )
    artifact.validate()
    return artifact
