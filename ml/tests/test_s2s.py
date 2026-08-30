import pickle

import numpy as np
import pandas as pd

from glideator_ml.s2s.artifact import S2SArtifact, recommend
from glideator_ml.s2s.data import (
    events_fingerprint,
    first_visits,
    split_pilots,
    split_temporal,
    temporal_walk_forward_events,
    walk_forward_events,
)
from glideator_ml.s2s.evaluation import evaluate
from glideator_ml.s2s.models import fit_contrastive, fit_svd
from glideator_ml.s2s.run import _model_seed, _split_seed


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


def test_temporal_split_uses_only_past_training_data_and_keeps_prior_history():
    visits = first_visits(_raw_visits())
    cutoff = "2026-01-03"
    split = split_temporal(visits, cutoff=cutoff)

    assert split.train_visits["visit_at"].max() < pd.Timestamp(cutoff)
    assert split.eval_visits["visit_at"].min() >= pd.Timestamp(cutoff)

    events = temporal_walk_forward_events(visits, cutoff=cutoff)
    assert ("p1", (1,), 2) in events
    assert ("p1", (1, 2), 3) in events

    for pilot, prefix, target in events:
        ordered = (
            visits[visits["pilot"] == pilot]
            .sort_values(["visit_at", "site_id"])["site_id"]
            .tolist()
        )
        position = ordered.index(target)
        assert list(prefix) == ordered[:position]


def test_benchmark_split_seed_is_independent_from_model_seed():
    config = {
        "seed": 99,
        "data": {"split_seed": 42},
        "model": {"name": "contrastive", "seed": 46},
    }
    assert _split_seed(config) == 42
    assert _model_seed(config) == 46

    # Old configs remain reproducible via the legacy top-level fallback.
    legacy = {"seed": 7, "data": {}, "model": {"name": "svd"}}
    assert _split_seed(legacy) == 7
    assert _model_seed(legacy) == 7


def test_eval_set_fingerprint_identifies_exact_walk_forward_benchmark():
    visits = first_visits(_raw_visits())
    split = split_pilots(visits, eval_fraction=0.5, seed=42)
    events = walk_forward_events(split.eval_visits)

    fingerprint = events_fingerprint(events)
    assert fingerprint == events_fingerprint(list(events))

    changed = list(events)
    pilot, prefix, target = changed[0]
    changed[0] = (pilot, prefix, target + 1000)
    assert events_fingerprint(changed) != fingerprint


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

    events = [
        ("heldout-a", (1,), 2),
        ("heldout-b", (2, 1), 3),
        ("heldout-c", (1, 2, 3, 4), 999),
    ]
    metrics = evaluate(artifact_a, events, visits, ks=[1, 3])

    assert metrics["events"] == 3
    assert "hit_rate_at_1" in metrics
    assert "mrr_at_3" in metrics
    assert "ndcg_at_3" in metrics
    assert "end_to_end_hit_rate_at_3" in metrics
    assert "coverage_at_3" in metrics
    assert "avg_log_popularity_at_3" in metrics
    assert metrics["history_1_events"] == 1
    assert metrics["history_2_3_events"] == 1
    assert metrics["history_4_plus_events"] == 1
    assert metrics["target_cold_start_events"] == 1
    assert metrics["cold_start_target_rate"] == 1 / 3


def test_contrastive_model_exports_backend_compatible_embeddings():
    visits = first_visits(_raw_visits())
    artifact = fit_contrastive(
        visits,
        n_factors=4,
        epochs=1,
        learning_rate=5e-3,
        weight_decay=1e-4,
        temperature=0.1,
        batch_size=4,
        negative_samples=1,
        add_inbatch_negatives=False,
        seed=42,
        device="cpu",
    )

    assert artifact.matrix.shape == (4, 4)
    np.testing.assert_allclose(
        np.linalg.norm(artifact.matrix, axis=1),
        np.ones(4),
        atol=1e-6,
    )
    assert artifact.metadata["model_type"] == "contrastive"
