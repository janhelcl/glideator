import pickle
import os

import numpy as np


# Load embeddings from the models directory
embeddings_path = os.path.join(os.path.dirname(__file__), '..', 'models', 's2s_covisit_embeddings.pkl')
EMBEDDINGS = pickle.load(open(embeddings_path, 'rb'))


def vector_search(source_ids, top_k=10):
    """
    Performs a vector-based search to find the top_k most similar sites to a set of source site IDs,
    based on cosine similarity of their learned embeddings.

    Args:
        source_ids (list[int]): List of site IDs to use as the query. These are mapped to embedding indices.
        top_k (int, optional): The number of top recommendations to return. Defaults to 10.

    Returns:
        list[tuple[int, float]] or None: A list of tuples (site_id, similarity_score) for the top_k most similar sites,
        excluding any sites in source_ids. If no valid source_ids are given, returns None.
    """
    idxs = [EMBEDDINGS["site_to_idx"].get(int(site_id)) for site_id in source_ids]
    idxs = [i for i in idxs if i is not None]
    if not idxs:
        return None
    E = EMBEDDINGS["matrix"]
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
        sid = EMBEDDINGS["idx_to_site"][j]
        out.append((sid, float(scores[j])))
    return out