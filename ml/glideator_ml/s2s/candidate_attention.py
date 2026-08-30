from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np
import pandas as pd

from .artifact import S2SArtifact

logger = logging.getLogger(__name__)


def fit_candidate_attention(
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
    attention_scale_init: float,
    seed: int,
    device: str = "auto",
    metadata: dict[str, Any] | None = None,
) -> S2SArtifact:
    """Fit residual candidate-conditioned attention for next-site discovery."""
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader, Dataset
    except ImportError as exc:
        raise RuntimeError(
            "Candidate-attention S2S training requires the 'contrastive' extra"
        ) from exc

    if train_visits.empty:
        raise ValueError("Cannot fit candidate-attention S2S on an empty training set")
    if n_factors <= 0:
        raise ValueError("n_factors must be positive")
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
        raise ValueError("Candidate-attention S2S needs at least one training episode")

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
        max_history = max(len(history) for history in histories)
        padded = np.zeros((len(histories), max_history), dtype=np.int64)
        mask = np.zeros((len(histories), max_history), dtype=np.bool_)
        for row, history in enumerate(histories):
            padded[row, : len(history)] = history
            mask[row, : len(history)] = True
        return (
            torch.as_tensor(padded, dtype=torch.long),
            torch.as_tensor(mask, dtype=torch.bool),
            torch.as_tensor(targets, dtype=torch.long),
        )

    class CandidateAttentionModel(nn.Module):
        def __init__(self):
            super().__init__()
            dimension = int(n_factors)
            self.item_embeddings = nn.Embedding(len(sites), dimension)
            self.query_projection = nn.Linear(dimension, dimension, bias=False)
            self.key_projection = nn.Linear(dimension, dimension, bias=False)
            self.value_projection = nn.Linear(dimension, dimension, bias=False)
            self.attention_scale = nn.Parameter(
                torch.tensor(float(attention_scale_init), dtype=torch.float32)
            )

            nn.init.normal_(self.item_embeddings.weight, std=0.02)
            nn.init.eye_(self.query_projection.weight)
            nn.init.eye_(self.key_projection.weight)
            nn.init.eye_(self.value_projection.weight)

        def score_candidates(self, histories, history_mask, candidate_ids):
            # Raw summed embeddings preserve the strong contrastive baseline.
            raw_history = self.item_embeddings(histories)
            mask_float = history_mask.unsqueeze(-1).to(raw_history.dtype)
            base = (raw_history * mask_float).sum(dim=1)
            base = nn.functional.normalize(base, dim=1)

            normalized_history = nn.functional.normalize(raw_history, dim=2)
            candidates = nn.functional.normalize(
                self.item_embeddings(candidate_ids),
                dim=2,
            )

            # Embeddings are unit length; scale Q/K inputs by sqrt(d) so the
            # standard scaled-dot-product logits have Transformer-like magnitude.
            root_d = math.sqrt(float(n_factors))
            queries = self.query_projection(candidates * root_d)
            keys = self.key_projection(normalized_history * root_d)
            values = self.value_projection(normalized_history)

            attention_logits = torch.einsum(
                "bcd,bld->bcl", queries, keys
            ) / root_d
            attention_logits = attention_logits.masked_fill(
                ~history_mask.unsqueeze(1),
                torch.finfo(attention_logits.dtype).min,
            )
            attention = torch.softmax(attention_logits, dim=2)
            context = torch.einsum("bcl,bld->bcd", attention, values)

            candidate_queries = nn.functional.normalize(
                base.unsqueeze(1) + self.attention_scale * context,
                dim=2,
            )
            return (candidate_queries * candidates).sum(dim=2)

        def forward(self, histories, history_mask, targets, negatives):
            candidate_ids = torch.cat([targets.unsqueeze(1), negatives], dim=1)
            logits = self.score_candidates(histories, history_mask, candidate_ids)

            if add_inbatch_negatives:
                inbatch_ids = targets.unsqueeze(0).expand(len(targets), -1)
                inbatch_logits = self.score_candidates(
                    histories,
                    history_mask,
                    inbatch_ids,
                )
                inbatch_logits = inbatch_logits - torch.eye(
                    len(targets),
                    device=inbatch_logits.device,
                ) * 1e9
                logits = torch.cat([logits, inbatch_logits], dim=1)

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

    model = CandidateAttentionModel().to(resolved_device)
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
        for histories, history_mask, targets in loader:
            histories = histories.to(resolved_device)
            history_mask = history_mask.to(resolved_device)
            targets = targets.to(resolved_device)

            weights = sampling_weights.expand(len(targets), -1).clone()
            batch_rows = torch.arange(len(targets), device=resolved_device)
            expanded_rows = batch_rows.unsqueeze(1).expand_as(histories)
            weights[
                expanded_rows[history_mask],
                histories[history_mask],
            ] = 0
            weights[batch_rows, targets] = 0

            available = (weights > 0).sum(dim=1)
            if torch.any(available < int(negative_samples)):
                raise ValueError(
                    "negative_samples exceeds the available unseen catalog "
                    "for at least one candidate-attention training episode"
                )
            negatives = torch.multinomial(
                weights,
                num_samples=int(negative_samples),
                replacement=False,
                generator=sampling_generator,
            )

            optimizer.zero_grad(set_to_none=True)
            loss = model(histories, history_mask, targets, negatives)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            total_loss += float(loss.detach()) * len(targets)
            examples += len(targets)

        final_loss = total_loss / examples
        logger.info(
            "Candidate-attention S2S epoch %d/%d loss=%.4f scale=%.4f",
            epoch,
            epochs,
            final_loss,
            float(model.attention_scale.detach()),
        )

    model.eval()
    with torch.no_grad():
        raw_embeddings = (
            model.item_embeddings.weight.detach().cpu().numpy().astype(np.float32)
        )
        embeddings = nn.functional.normalize(
            model.item_embeddings.weight,
            dim=1,
        ).cpu().numpy().astype(np.float32)
        scorer = {
            "type": "candidate_attention",
            "history_matrix": raw_embeddings,
            "query_weight": (
                model.query_projection.weight.detach().cpu().numpy().astype(np.float32)
            ),
            "key_weight": (
                model.key_projection.weight.detach().cpu().numpy().astype(np.float32)
            ),
            "value_weight": (
                model.value_projection.weight.detach().cpu().numpy().astype(np.float32)
            ),
            "attention_scale": float(model.attention_scale.detach().cpu()),
        }

    artifact = S2SArtifact(
        site_to_idx=site_to_idx,
        idx_to_site=sites,
        matrix=embeddings,
        scorer=scorer,
        metadata={
            "model_type": "candidate_attention",
            "n_factors": int(n_factors),
            "attention_heads": 1,
            "attention_scale_init": float(attention_scale_init),
            "attention_scale_final": float(scorer["attention_scale"]),
            "residual_base": "normalized_raw_embedding_sum",
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
