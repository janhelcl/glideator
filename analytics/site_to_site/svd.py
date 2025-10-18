import logging
import numpy as np
import pickle
from scipy.sparse import csr_matrix

logger = logging.getLogger(__name__)

class SVDRecommender:
    """
    PureSVD-style item recommender for 'new site discovery'.

    Key changes vs. previous version:
      • Uses centroid-cosine scoring (sum favorites in factor space -> cosine).
      • Uses smoothed positive IDF: log((N+1)/(df+1)) + 1.
      • Uses exact dense SVD (pilots x sites) for 250 sites (fast & stable).

    Hyperparams:
      n_factors   : rank k (try 32/64/96)
      apply_idf   : apply IDF column weights before SVD
      sigma_power : singular value power p (try 1.0, 0.8)
      drop_top    : int, number of leading components to zero (e.g., 0 or 1)
    """

    def __init__(self, n_factors=64, apply_idf=True, sigma_power=1.0, drop_top=0):
        if n_factors < 1:
            raise ValueError("n_factors must be >= 1")
        if sigma_power < 0:
            raise ValueError("sigma_power must be >= 0")
        if drop_top < 0:
            raise ValueError("drop_top must be >= 0")

        self.n_factors   = int(n_factors)
        self.apply_idf   = apply_idf
        self.sigma_power = sigma_power
        self.drop_top    = drop_top

        # learned / cached
        self.E_norm = None                 # (n_sites, k) L2-normalized site embeddings
        self.idf_weights = None            # (n_sites,)
        self.site_to_idx = None
        self.idx_to_site = None
        self.site_id_to_name = None
        self.pilot_to_idx = None

        # raw SVD bits (optional to persist)
        self.U = None
        self.sigma = None
        self.Vt = None

    def _compute_idf(self, X: csr_matrix) -> np.ndarray:
        """Smoothed positive IDF per site column."""
        n_pilots = X.shape[0]
        # number of pilots with ANY interaction in the site column
        df = np.asarray((X > 0).sum(axis=0)).ravel()
        idf = np.log((n_pilots + 1.0) / (df + 1.0)) + 1.0
        return idf.astype(np.float32)

    def fit(self, interaction_matrix: csr_matrix,
            pilot_to_idx: dict, site_to_idx: dict, idx_to_site: dict,
            site_id_to_name: dict | None = None):
        """
        Train on pilot×site binary/weighted first-visit matrix (CSR, shape [n_pilots, n_sites]).
        """
        if not isinstance(interaction_matrix, csr_matrix):
            raise TypeError("interaction_matrix must be CSR sparse matrix")

        self.pilot_to_idx = pilot_to_idx
        self.site_to_idx = site_to_idx
        self.idx_to_site = idx_to_site
        self.site_id_to_name = site_id_to_name or {}

        n_pilots, n_sites = interaction_matrix.shape
        k = min(self.n_factors, n_sites, n_pilots)

        # --- Column weighting (IDF) ---
        if self.apply_idf:
            self.idf_weights = self._compute_idf(interaction_matrix)
            logger.info("IDF: min=%.3f mean=%.3f max=%.3f",
                        float(self.idf_weights.min()),
                        float(self.idf_weights.mean()),
                        float(self.idf_weights.max()))
        else:
            self.idf_weights = np.ones(n_sites, dtype=np.float32)

        # --- Build dense pilots×sites matrix (float32) and apply IDF ---
        # For 31k x 250 this is ~31M floats (~125MB float32 if fully dense).
        # If memory tight, you can densify per-batch; with 250 items it's usually fine.
        M = interaction_matrix.astype(np.float32).toarray()
        M *= self.idf_weights[None, :]

        # --- Exact SVD (descending singular values) ---
        # numpy.linalg.svd returns s sorted descending already.
        U, s, Vt = np.linalg.svd(M, full_matrices=False)
        self.U, self.sigma, self.Vt = U[:, :k], s[:k], Vt[:k, :]

        logger.info("SVD shapes: U=%s s=%s Vt=%s", self.U.shape, self.sigma.shape, self.Vt.shape)

        # --- Sigma power transform ---
        if self.sigma_power != 1.0:
            sig = np.power(self.sigma, self.sigma_power)
        else:
            sig = self.sigma

        # --- Site embeddings: (Sigma^p * Vt)^T => (n_sites, k) ---
        E = (sig[:, None] * self.Vt).T   # broadcast multiply

        # --- Optional: drop top components to reduce global-popularity axis ---
        if self.drop_top > 0:
            c = min(self.drop_top, E.shape[1])
            E[:, :c] = 0.0

        # --- L2-normalize rows (store normalized embeddings for cosine scoring) ---
        norms = np.linalg.norm(E, axis=1, keepdims=True) + 1e-12
        self.E_norm = (E / norms).astype(np.float32)

        return self

    # ---------- Inference (centroid-cosine) ----------

    def _site_idx(self, site_id: int) -> int | None:
        return self.site_to_idx.get(site_id)

    def get_similar_sites(self, site_id: int, top_k: int = 10):
        """Cosine neighbors using normalized embeddings."""
        i = self._site_idx(site_id)
        if i is None:
            return None
        sims = self.E_norm @ self.E_norm[i]       # cosine
        sims[i] = -np.inf
        top = np.argpartition(-sims, top_k)[:top_k]
        top = top[np.argsort(-sims[top])]
        out = []
        for j in top:
            sid = self.idx_to_site[j]
            out.append((sid, self.site_id_to_name.get(sid, "Unknown"), float(sims[j])))
        return out

    def get_recommendations(self, history_sites: list[int], top_k: int = 10):
        """Centroid-of-history -> cosine over unseen sites."""
        idxs = [self._site_idx(s) for s in history_sites if self._site_idx(s) is not None]
        if not idxs:
            return None
        q = self.E_norm[idxs].sum(axis=0)
        q /= (np.linalg.norm(q) + 1e-12)
        scores = self.E_norm @ q

        # mask already visited
        for i in idxs:
            scores[i] = -np.inf

        top = np.argpartition(-scores, top_k)[:top_k]
        top = top[np.argsort(-scores[top])]
        out = []
        for j in top:
            sid = self.idx_to_site[j]
            out.append((sid, self.site_id_to_name.get(sid, "Unknown"), float(scores[j])))
        return out

    # ---------- Persistence ----------

    def save(self, filepath: str):
        blob = dict(
            model_type="SVD",
            n_factors=self.n_factors,
            apply_idf=self.apply_idf,
            sigma_power=self.sigma_power,
            drop_top=self.drop_top,
            E_norm=self.E_norm,
            idf_weights=self.idf_weights,
            site_to_idx=self.site_to_idx,
            idx_to_site=self.idx_to_site,
            site_id_to_name=self.site_id_to_name,
            pilot_to_idx=self.pilot_to_idx,
            U=self.U, sigma=self.sigma, Vt=self.Vt,
        )
        with open(filepath, "wb") as f:
            pickle.dump(blob, f)
        logger.info("Saved SVDRecommender to %s", filepath)

    def load(self, filepath: str):
        with open(filepath, "rb") as f:
            blob = pickle.load(f)
        self.n_factors   = blob.get("n_factors", self.n_factors)
        self.apply_idf   = blob.get("apply_idf", self.apply_idf)
        self.sigma_power = blob.get("sigma_power", self.sigma_power)
        self.drop_top    = blob.get("drop_top", self.drop_top)

        self.E_norm = blob["E_norm"]
        self.idf_weights = blob.get("idf_weights", None)
        self.site_to_idx = blob["site_to_idx"]
        self.idx_to_site = blob["idx_to_site"]
        self.site_id_to_name = blob.get("site_id_to_name", {})
        self.pilot_to_idx = blob.get("pilot_to_idx", None)
        self.U = blob.get("U", None)
        self.sigma = blob.get("sigma", None)
        self.Vt = blob.get("Vt", None)

        logger.info("Loaded SVDRecommender from %s (k=%d, IDF=%s, p=%.3f, drop_top=%d)",
                    filepath, self.n_factors, self.apply_idf, self.sigma_power, self.drop_top)
        return self
