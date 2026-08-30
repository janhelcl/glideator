import pickle

import numpy as np
import pandas as pd

from glideator_ml.s2s.artifact import S2SArtifact, recommend
from glideator_ml.s2s.data import first_visits, split_pilots, walk_forward_events
from glideator_ml.s2s.evaluation import evaluate
from glideator_ml.s2s.models import fit_svd


def _raw_visits():
    return pd.DataFrame(
        [
            ("p1", 1, "2026-01-01", "10:00:00"),
            ("p1", 1, "2026-01-02", "10:00:00"),
            ("p1", 2, "2026-01-03", "10:00:00"),
            ("p1", 3, "2026-01-04", "10:00:00"),
            ("p2", 1, "2026-01-01", "10:00:00"),
            ("p2", 2, "2026-01-02", "10:00:00"),
            ("p2", 4, "2026-01-03", "10:00:00"),
            ("p3", 2, "2026-01-01", "10:00:00"),
            ("p3", 3, "2026-01-02", "10:00:00"),
            ("p3", 4, "2026-01-03", "10:00:00"),
            ("p4", 1, "2026-01-01", "10:00:00"),
            ("p4", 3, "2026-01-02", "10:00:00"),
            ("p4", 4, "2026-01-03", "10:00:00"),
        ],
        columns=["pilot", "site_id", "date", "start_time"],
    )


def test_first_visits_and_split_have_no_pilot_leakage():
    visits = first_visits(_raw_visits())
    assert len(visits[visits["pilot"] == "p1"]) == 3

    split = split_pilots(visits, eval_fraction=0.5, seed=42)
    train_pilots = set(split.train_visits["pilot"])
    eval_pilots = set(split.eval_visits["pilot"])
    assert train_pilots
    assert eval_pilots
    assert train_pilots.isdisjoint(eval_pilots)

    events = walk_forward_events(split.eval_visits)
    for pilot, prefix, target in events:
        ordered = (
            split.eval_visits[split.eval_visits["pilot"] == pilot]
            .sort_values("visit_at")["site_id"]
            .tolist()
        )
        position = len(prefix)
        assert list(prefix) == ordered[:position]
        assert target == ordered[position]


def test_artifact_is_backward_compatible_with_backend_pickle_contract(tmp_path):
    artifact = S2SArtifact(
        site_to_idx={1: 0, 2: 1, 3: 2},
        idx_to_site=[1, 2, 3],
        matrix=np.asarray(
            [
                [1.0, 0.0],
                [0.9, 0.1],
                [0.0, 1.0],
            ],
            dtype=np.float32,
        ),
        metadata={"model_type": "test"},
    )
    path = artifact.save(tmp_path / "artifact.pkl")
    with path.open("rb") as handle:
        payload = pickle.load(handle)

    assert {"site_to_idx", "idx_to_site", "matrix"} <= payload.keys()
    assert recommend(artifact, [1], top_k=1)[0][0] == 2


def test_svd_is_reproducible_and_evaluator_reports_ranking_metrics():
    visits = first_visits(_raw_visits())
    artifact_a = fit_svd(
        visits,
        n_factors=2,
        sigma_power=1.0,
        seed=7,
    )
    artifact_b = fit_svd(
        visits,
        n_factors=2,
        sigma_power=1.0,
        seed=7,
    )
    np.testing.assert_allclose(artifact_a.matrix, artifact_b.matrix)

    events = [("heldout", (1,), 2), ("heldout", (2,), 3)]
    metrics = evaluate(artifact_a, events, visits, ks=[1, 3])

    assert metrics["events"] == 2
    assert "hit_rate_at_1" in metrics
    assert "mrr_at_3" in metrics
    assert "ndcg_at_3" in metrics
    assert "coverage_at_3" in metrics
    assert "avg_log_popularity_at_3" in metrics
