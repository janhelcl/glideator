from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from .artifact import S2SArtifact

logger = logging.getLogger(__name__)


def fit_asymmetric(
    train_visits: pd.DataFrame,
    *,
    n_factors: int,
    epochs: int,
    learning_rate: float,
    weight_decay: float,
    temperature: float,
    batch_size: int,
    negative_samples: int,
    negative_sampling_power: float,
    add_inbatch_negatives: bool,
    seed: int,
    device: str = "auto",
    metadata: dict[str, Any] | None = None,
) -> S2SArtifact:
    """Fit additive S2S with separate source and target embedding tables."""
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, Dataset
    except ImportError as exc:
        raise RuntimeError(
            "Asymmetric S2S training requires the 'contrastive' extra"
        ) from exc

    if train_visits.empty:
        raise ValueError("Cannot fit asymmetric S2S on an empty training set")

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
        raise ValueError("Asymmetric S2S needs at least one training episode")

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

    class AsymmetricDiscoveryModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.source_embeddings = nn.EmbeddingBag(
                len(sites),
                int(n_factors),
                mode="sum",
                include_last_offset=True,
            )
            self.target_embeddings = nn.Embedding(len(sites), int(n_factors))
            nn.init.normal_(self.source_embeddings.weight, std=0.02)
            nn.init.normal_(self.target_embeddings.weight, std=0.02)

        def forward(self, flat, offsets, targets, negatives):
            query = nn.functional.normalize(
                self.source_embeddings(flat, offsets), dim=1
            )
            positive = nn.functional.normalize(
                self.target_embeddings(targets), dim=1
            )
            negative = nn.functional.normalize(
                self.target_embeddings(negatives), dim=2
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
            labels = torch.zeros(
                logits.size(0), dtype=torch.long, device=logits.device
            )
            return nn.functional.cross_entropy(logits / temperature, labels)

    resolved_device = (
        "cuda" if device == "auto" and torch.cuda.is_available() else device
    )
    if resolved_device == "auto":
        resolved_device = "cpu"

    model = AsymmetricDiscoveryModel().to(resolved_device)
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
        np.power(popularity + 1e-8, float(negative_sampling_power)),
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
            "Asymmetric S2S epoch %d/%d loss=%.4f",
            epoch,
            epochs,
            final_loss,
        )

    model.eval()
    with torch.no_grad():
        source_embeddings = nn.functional.normalize(
            model.source_embeddings.weight, dim=1
        ).cpu().numpy().astype(np.float32)
        target_embeddings = nn.functional.normalize(
            model.target_embeddings.weight, dim=1
        ).cpu().numpy().astype(np.float32)

    artifact = S2SArtifact(
        site_to_idx=site_to_idx,
        idx_to_site=sites,
        matrix=target_embeddings,
        scorer={
            "type": "asymmetric",
            "source_matrix": source_embeddings,
        },
        metadata={
            "model_type": "asymmetric",
            "n_factors": int(n_factors),
            "epochs": int(epochs),
            "learning_rate": float(learning_rate),
            "weight_decay": float(weight_decay),
            "temperature": float(temperature),
            "batch_size": int(batch_size),
            "negative_samples": int(negative_samples),
            "negative_sampling_power": float(negative_sampling_power),
            "add_inbatch_negatives": bool(add_inbatch_negatives),
            "seed": int(seed),
            "device": resolved_device,
            "train_pilots": int(train_visits["pilot"].nunique()),
            "train_episodes": len(episodes),
            "catalog_size": len(sites),
            "final_loss": final_loss,
            "requires_learned_scorer": True,
            **(metadata or {}),
        },
    )
    artifact.validate()
    return artifact
