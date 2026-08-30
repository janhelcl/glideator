from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from .artifact import S2SArtifact

logger = logging.getLogger(__name__)


def fit_transformed_additive(
    train_visits: pd.DataFrame,
    *,
    n_factors: int,
    phi_hidden_dim: int,
    rho_hidden_dim: int,
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
    """Fit per-site nonlinear transforms followed by additive history composition."""
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, Dataset
    except ImportError as exc:
        raise RuntimeError(
            "Transformed-additive S2S training requires the 'contrastive' extra"
        ) from exc

    if train_visits.empty:
        raise ValueError("Cannot fit transformed-additive S2S on an empty training set")
    if n_factors <= 0 or phi_hidden_dim <= 0 or rho_hidden_dim <= 0:
        raise ValueError("Transformed-additive dimensions must be positive")
    if negative_samples <= 0:
        raise ValueError("negative_samples must be positive")

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
        raise ValueError("Transformed-additive S2S needs at least one training episode")

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

    class TransformedAdditiveDiscoveryModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.item_embeddings = nn.Embedding(len(sites), int(n_factors))
            self.phi = nn.Sequential(
                nn.Linear(int(n_factors), int(phi_hidden_dim)),
                nn.ReLU(),
                nn.Linear(int(phi_hidden_dim), int(n_factors)),
            )
            self.rho = nn.Sequential(
                nn.Linear(int(n_factors), int(rho_hidden_dim)),
                nn.ReLU(),
                nn.Linear(int(rho_hidden_dim), int(n_factors)),
            )
            nn.init.normal_(self.item_embeddings.weight, std=0.02)

        def encode_history(self, flat, offsets):
            items = nn.functional.normalize(
                self.item_embeddings(flat),
                dim=1,
            )
            transformed = self.rho(self.phi(items))
            lengths = offsets[1:] - offsets[:-1]
            batch_rows = torch.repeat_interleave(
                torch.arange(len(lengths), device=flat.device),
                lengths,
            )
            pooled = torch.zeros(
                (len(lengths), int(n_factors)),
                dtype=transformed.dtype,
                device=transformed.device,
            )
            pooled.index_add_(0, batch_rows, transformed)
            return nn.functional.normalize(pooled, dim=1)

        def forward(self, flat, offsets, targets, negatives):
            query = self.encode_history(flat, offsets)
            positive = nn.functional.normalize(
                self.item_embeddings(targets),
                dim=1,
            )
            negative = nn.functional.normalize(
                self.item_embeddings(negatives),
                dim=2,
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
                logits.size(0),
                dtype=torch.long,
                device=logits.device,
            )
            return nn.functional.cross_entropy(logits / temperature, labels)

    resolved_device = (
        "cuda" if device == "auto" and torch.cuda.is_available() else device
    )
    if resolved_device == "auto":
        resolved_device = "cpu"

    model = TransformedAdditiveDiscoveryModel().to(resolved_device)
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
            available = (weights > 0).sum(dim=1)
            if torch.any(available < int(negative_samples)):
                raise ValueError(
                    "negative_samples exceeds the available unseen catalog "
                    "for at least one transformed-additive training episode"
                )
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
            "Transformed-additive S2S epoch %d/%d loss=%.4f",
            epoch,
            epochs,
            final_loss,
        )

    model.eval()
    with torch.no_grad():
        embeddings = nn.functional.normalize(
            model.item_embeddings.weight,
            dim=1,
        ).cpu().numpy().astype(np.float32)
        scorer = {
            "type": "transformed_additive",
            "phi_w1": model.phi[0].weight.detach().cpu().numpy().astype(np.float32),
            "phi_b1": model.phi[0].bias.detach().cpu().numpy().astype(np.float32),
            "phi_w2": model.phi[2].weight.detach().cpu().numpy().astype(np.float32),
            "phi_b2": model.phi[2].bias.detach().cpu().numpy().astype(np.float32),
            "rho_w1": model.rho[0].weight.detach().cpu().numpy().astype(np.float32),
            "rho_b1": model.rho[0].bias.detach().cpu().numpy().astype(np.float32),
            "rho_w2": model.rho[2].weight.detach().cpu().numpy().astype(np.float32),
            "rho_b2": model.rho[2].bias.detach().cpu().numpy().astype(np.float32),
        }

    artifact = S2SArtifact(
        site_to_idx=site_to_idx,
        idx_to_site=sites,
        matrix=embeddings,
        scorer=scorer,
        metadata={
            "model_type": "transformed_additive",
            "n_factors": int(n_factors),
            "phi_hidden_dim": int(phi_hidden_dim),
            "rho_hidden_dim": int(rho_hidden_dim),
            "aggregation": "sum_after_phi_rho",
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
