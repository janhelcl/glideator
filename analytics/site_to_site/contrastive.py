"""
Contrastive learning module for site discovery recommender.

Implements PyTorch-based contrastive learning for site discovery:
- DiscoveryEpisodes: Dataset for contrastive learning episodes
- DiscoveryModel: PyTorch module with InfoNCE loss (+ in-batch negatives)
- ContrastiveRecommender: Wrapper for evaluation interface

Key ideas:
- Train on walk-forward episodes (history -> next first-visit).
- Negatives from UNSEEN-at-t sites, popularity^0.75, vectorized sampling.
- Serving = centroid cosine over L2-normalized item embeddings.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader

logger = logging.getLogger(__name__)

# -----------------------------
# Reproducibility helpers
# -----------------------------

def set_global_seed(seed: int = 42):
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    # torch.backends.cudnn.deterministic = True  # uncomment if you require strict determinism (slower)
    # torch.backends.cudnn.benchmark = False


# -----------------------------
# Dataset
# -----------------------------

class DiscoveryEpisodes(Dataset):
    """
    PyTorch Dataset for contrastive learning episodes.

    Each item returns: (histories_bag, pos_index, neg_indices)
    - histories_bag is flattened indices + offsets consumed by EmbeddingBag.
    - Negatives are sampled from sites UNSEEN at cutoff (not in history, not pos).
    """

    def __init__(
        self,
        episodes: List[Dict[str, Any]],
        site_to_idx: Dict[int, int],
        n_items: int,
        k_neg: int = 50,
        pop_weights: Optional[np.ndarray] = None,
        hard_neighbors: Optional[Dict[int, List[int]]] = None,
        hard_frac: float = 0.2,
        seed: int = 42,
    ):
        """
        Args:
            episodes: List of dicts with keys {'history_sites', 'target_site'}
            site_to_idx: Dict mapping site_id -> index [0..n_items)
            n_items: Total number of sites
            k_neg: # negatives per episode
            pop_weights: Optional per-site popularity counts; will be used as pop^0.75
            hard_neighbors: Optional dict idx -> list of hard negative candidate idx
            hard_frac: Fraction of negatives to draw from hard neighbors (0..1)
            seed: RNG seed (deterministic sampling)
        """
        self.episodes = episodes
        self.site_to_idx = {int(k): int(v) for k, v in site_to_idx.items()}
        self.n_items = int(n_items)
        self.k_neg = int(k_neg)
        self.hard_neighbors = hard_neighbors or {}
        self.hard_frac = float(hard_frac)
        self.rng = np.random.default_rng(seed)

        # Popularity^0.75 distribution (or uniform)
        if pop_weights is None:
            self.base_prob = np.ones(self.n_items, dtype=np.float64) / self.n_items
        else:
            pw = np.power(np.asarray(pop_weights, dtype=np.float64) + 1e-8, 0.75)
            self.base_prob = pw / pw.sum()

    def __len__(self) -> int:
        return len(self.episodes)

    def _masked_choice(self, mask: np.ndarray, k: int) -> np.ndarray:
        """Sample k indices without replacement from where mask==True, weighted by base_prob."""
        # mask: True for candidate items
        if not mask.any():
            return np.empty((0,), dtype=np.int64)
        p = self.base_prob * mask
        s = p.sum()
        if s <= 0:
            return np.empty((0,), dtype=np.int64)
        p = p / s
        k = min(k, int(mask.sum()))
        return self.rng.choice(self.n_items, size=k, replace=False, p=p).astype(np.int64)

    def __getitem__(self, idx: int) -> Tuple[Tuple[torch.Tensor, torch.Tensor], np.int64, np.ndarray]:
        ep = self.episodes[idx]
        hist_sites = ep["history_sites"]
        pos_site = ep["target_site"]

        # Map to indices; drop unknowns
        hist_idx = [self.site_to_idx[s] for s in hist_sites if int(s) in self.site_to_idx]
        if not hist_idx:
            # resample another episode deterministically
            return self[(idx + 1) % len(self)]

        pos = self.site_to_idx.get(int(pos_site))
        if pos is None:
            return self[(idx + 1) % len(self)]

        # Block history + pos
        blocked = np.zeros(self.n_items, dtype=bool)
        blocked[hist_idx] = True
        blocked[pos] = True

        # Hard negatives (optional)
        n_hard = int(round(self.hard_frac * self.k_neg))
        hard = []
        if n_hard > 0 and pos in self.hard_neighbors:
            for cand in self.hard_neighbors[pos]:
                if 0 <= cand < self.n_items and not blocked[cand]:
                    hard.append(int(cand))
                    if len(hard) >= n_hard:
                        break
        hard = np.array(hard, dtype=np.int64)

        # Popularity-sampled negatives for the rest
        n_rem = max(0, self.k_neg - len(hard))
        cand_mask = ~blocked
        # avoid double-dipping into hard negatives
        if len(hard) > 0:
            cand_mask[hard] = False
        soft = self._masked_choice(cand_mask, n_rem)

        negs = np.concatenate([hard, soft]) if len(hard) > 0 else soft
        if negs.size == 0:
            return self[(idx + 1) % len(self)]

        # Return histories for EmbeddingBag (flat indices + offsets)
        # Here we keep ragged histories per batch; collate will flatten.
        return (np.array(hist_idx, dtype=np.int64),), np.int64(pos), negs


# -----------------------------
# Collate (EmbeddingBag-friendly)
# -----------------------------

def collate_episodes(batch):
    """
    Returns:
        histories_bag: (flat_indices [N], offsets [B]) for EmbeddingBag(mode='sum')
        pos: [B] LongTensor
        neg: [B, K] LongTensor
    """
    Hs, Ps, Ns = [], [], []
    for (hist_tuple,), pos, neg in batch:
        Hs.append(hist_tuple)
        Ps.append(pos)
        Ns.append(neg)

    # Build flat indices + offsets
    offsets = [0]
    flat = []
    for h in Hs:
        flat.extend(h.tolist())
        offsets.append(offsets[-1] + len(h))
    flat = torch.tensor(flat, dtype=torch.long)
    offsets = torch.tensor(offsets, dtype=torch.long)  # length B

    pos = torch.as_tensor(np.array(Ps), dtype=torch.long)
    neg = torch.as_tensor(np.stack(Ns), dtype=torch.long)
    return (flat, offsets), pos, neg


# -----------------------------
# Model
# -----------------------------

class DiscoveryModel(nn.Module):
    """
    Contrastive site-embedding model:
      - Centroid query via EmbeddingBag(sum)
      - InfoNCE with temperature
      - In-batch negatives (other positives act as extra negatives)
    """

    def __init__(self, n_items: int, dim: int = 64):
        super().__init__()
        self.n_items = int(n_items)
        self.dim = int(dim)
        self.item_emb = nn.Embedding(self.n_items, self.dim)
        # EmbeddingBag with sum; tie weights to item_emb
        self.bag = nn.EmbeddingBag(self.n_items, self.dim, mode="sum", include_last_offset=True)
        self.bag.weight = self.item_emb.weight  # tie
        nn.init.normal_(self.item_emb.weight, std=0.02)

    def forward(
        self,
        histories_bag: Tuple[torch.Tensor, torch.Tensor],
        pos_idx: torch.Tensor,
        neg_idx: torch.Tensor,
        tau: float = 0.1,
        add_inbatch_neg: bool = True,
        l2_reg: float = 0.0,
    ) -> torch.Tensor:
        """
        Args:
            histories_bag: (flat_indices [N], offsets [B])
            pos_idx: [B]
            neg_idx: [B, K]
            tau: temperature
            add_inbatch_neg: if True, add in-batch positives as negatives
            l2_reg: optional L2 penalty on embeddings
        """
        flat, offsets = histories_bag
        # Centroid queries
        q = self.bag(flat, offsets)                       # [B, d]
        q = nn.functional.normalize(q, dim=1)

        # Normalize item embeddings for positives / negatives
        e_pos = nn.functional.normalize(self.item_emb(pos_idx), dim=1)     # [B, d]
        e_neg = nn.functional.normalize(self.item_emb(neg_idx), dim=2)     # [B, K, d]

        pos_logit = (q * e_pos).sum(dim=1, keepdim=True)                   # [B,1]
        neg_logit = torch.einsum("bd,bkd->bk", q, e_neg)                   # [B,K]

        # In-batch negatives (exclude diagonal)
        if add_inbatch_neg:
            ibn = q @ e_pos.T                                              # [B,B]
            ibn = ibn - torch.eye(ibn.size(0), device=ibn.device) * 1e9    # mask self
            neg_logit = torch.cat([neg_logit, ibn], dim=1)                 # [B, K+B]

        logits = torch.cat([pos_logit, neg_logit], dim=1) / tau            # [B, 1+K(+B)]
        labels = torch.zeros(logits.size(0), dtype=torch.long, device=logits.device)
        loss = nn.functional.cross_entropy(logits, labels)

        if l2_reg > 0:
            loss = loss + l2_reg * (self.item_emb.weight.pow(2).sum())

        return loss

    @torch.no_grad()
    def item_norm(self) -> torch.Tensor:
        """Return L2-normalized item embeddings for inference: [n_items, dim]."""
        return nn.functional.normalize(self.item_emb.weight, dim=1)


# -----------------------------
# Training loop
# -----------------------------

def train_discovery(
    model: DiscoveryModel,
    loader: DataLoader,
    epochs: int = 5,
    lr: float = 5e-3,
    weight_decay: float = 1e-4,
    tau: float = 0.1,
    device: str = "cuda" if torch.cuda.is_available() else "cpu",
    grad_clip: float = 1.0,
    add_inbatch_neg: bool = True,
    l2_reg: float = 0.0,
    use_amp: bool = False,
) -> DiscoveryModel:
    """
    Train the contrastive model.
    """
    model.to(device)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scaler = torch.cuda.amp.GradScaler(enabled=(use_amp and device.startswith("cuda")))

    for ep in range(1, epochs + 1):
        model.train()
        running = 0.0
        count = 0
        for histories_bag, pos, neg in loader:
            flat, offsets = histories_bag
            flat = flat.to(device); offsets = offsets.to(device)
            pos = pos.to(device); neg = neg.to(device)

            opt.zero_grad(set_to_none=True)
            if scaler.is_enabled():
                with torch.cuda.amp.autocast():
                    loss = model((flat, offsets), pos, neg, tau=tau,
                                 add_inbatch_neg=add_inbatch_neg, l2_reg=l2_reg)
                scaler.scale(loss).backward()
                if grad_clip is not None:
                    scaler.unscale_(opt)
                    nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                scaler.step(opt); scaler.update()
            else:
                loss = model((flat, offsets), pos, neg, tau=tau,
                             add_inbatch_neg=add_inbatch_neg, l2_reg=l2_reg)
                loss.backward()
                if grad_clip is not None:
                    nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
                opt.step()

            bs = pos.size(0)
            running += float(loss) * bs
            count += bs

        logger.info(f"[epoch {ep}] loss={running / max(1, count):.4f}")

    return model


# -----------------------------
# Inference wrapper
# -----------------------------

class ContrastiveRecommender:
    """
    Lightweight wrapper for evaluation/serving:
      - centroid cosine with cached normalized embeddings
      - hardened ID handling
    """

    def __init__(
        self,
        model: DiscoveryModel,
        site_to_idx: Dict[int, int],
        idx_to_site: Dict[int, int],
        site_id_to_name: Optional[Dict[int, str]] = None,
        device: str = "cpu",
    ):
        self.model = model.to(device)
        self.site_to_idx = {int(k): int(v) for k, v in site_to_idx.items()}
        self.idx_to_site = {int(k): int(v) for k, v in idx_to_site.items()}
        self.site_id_to_name = site_id_to_name or {}
        self.device = device

        self._item_embeddings = None  # np.ndarray [n_items, dim]
        self._update_embeddings()

    def _update_embeddings(self):
        self.model.eval()
        with torch.no_grad():
            self._item_embeddings = self.model.item_norm().cpu().numpy()

    def _idx(self, site_id: int) -> Optional[int]:
        try:
            return self.site_to_idx.get(int(site_id))
        except Exception:
            return None

    def get_recommendations(self, history_sites: List[int], top_k: int = 10) -> Optional[List[Tuple[int, str, float]]]:
        idxs = [self._idx(s) for s in history_sites]
        idxs = [i for i in idxs if i is not None]
        if not idxs:
            return None

        E = self._item_embeddings
        q = E[idxs].sum(axis=0)
        q_norm = np.linalg.norm(q)
        if q_norm == 0.0:
            return None
        q = q / q_norm

        scores = E @ q
        for i in idxs:  # mask visited
            scores[i] = -np.inf

        if top_k <= 0:
            return []
        top = np.argpartition(-scores, min(top_k, scores.size - 1))[:top_k]
        top = top[np.argsort(-scores[top])]

        out = []
        for j in top:
            sid = self.idx_to_site[j]
            out.append((sid, self.site_id_to_name.get(sid, "Unknown"), float(scores[j])))
        return out

    def get_similar_sites(self, site_id: int, top_k: int = 10) -> Optional[List[Tuple[int, str, float]]]:
        j = self._idx(site_id)
        if j is None:
            return None
        E = self._item_embeddings
        v = E[j]
        scores = E @ v
        scores[j] = -np.inf
        top = np.argpartition(-scores, min(top_k, scores.size - 1))[:top_k]
        top = top[np.argsort(-scores[top])]
        out = []
        for i in top:
            sid = self.idx_to_site[i]
            out.append((sid, self.site_id_to_name.get(sid, "Unknown"), float(scores[i])))
        return out

    def save(self, filepath: str):
        checkpoint = {
            "model_state_dict": self.model.state_dict(),
            "site_to_idx": self.site_to_idx,
            "idx_to_site": self.idx_to_site,
            "site_id_to_name": self.site_id_to_name,
            "model_config": {"n_items": self.model.n_items, "dim": self.model.dim},
        }
        torch.save(checkpoint, filepath)
        logger.info("Saved ContrastiveRecommender to %s", filepath)

    @classmethod
    def load(cls, filepath: str, device: str = "cpu") -> "ContrastiveRecommender":
        checkpoint = torch.load(filepath, map_location=device)
        cfg = checkpoint["model_config"]
        model = DiscoveryModel(n_items=int(cfg["n_items"]), dim=int(cfg["dim"]))
        model.load_state_dict(checkpoint["model_state_dict"])
        rec = cls(
            model=model,
            site_to_idx=checkpoint["site_to_idx"],
            idx_to_site=checkpoint["idx_to_site"],
            site_id_to_name=checkpoint.get("site_id_to_name", {}),
            device=device,
        )
        logger.info("Loaded ContrastiveRecommender from %s", filepath)
        return rec


# -----------------------------
# Minimal usage example (pseudo)
# -----------------------------
if __name__ == "__main__":
    set_global_seed(42)

    # episodes = [{"history_sites":[...], "target_site": s_pos}, ...]  # build from walk-forward on TRAIN PILOTS
    # site_to_idx, idx_to_site = {...}, {...}
    # pop_weights = np.array([...])  # per-site popularity counts (e.g., # pilots with first-visit in train)
    # hard_neighbors = {idx: [neighbor_idx1, ...], ...}  # optional

    # ds = DiscoveryEpisodes(episodes, site_to_idx, n_items=len(idx_to_site),
    #                        k_neg=50, pop_weights=pop_weights,
    #                        hard_neighbors=hard_neighbors, hard_frac=0.2, seed=42)
    # dl = DataLoader(ds, batch_size=512, shuffle=True, collate_fn=collate_episodes, num_workers=0)

    # model = DiscoveryModel(n_items=len(idx_to_site), dim=64)
    # train_discovery(model, dl, epochs=5, lr=5e-3, weight_decay=1e-4, tau=0.1,
    #                 device="cuda" if torch.cuda.is_available() else "cpu",
    #                 grad_clip=1.0, add_inbatch_neg=True, l2_reg=0.0, use_amp=True)

    # rec = ContrastiveRecommender(model, site_to_idx, idx_to_site, site_id_to_name={})
    # recs = rec.get_recommendations(history_sites=[...], top_k=10)
    # print(recs)
