from __future__ import annotations

from pathlib import Path

from glideator_ml.config import load_config


ROOT = Path(__file__).parents[1]
BASELINE = ROOT / "configs" / "xc" / "baselines" / "conventional_mlp.yaml"
SWEEP_DIR = ROOT / "configs" / "xc" / "optimization" / "site_embedding"
CANDIDATES = {
    8: SWEEP_DIR / "embedding_8.yaml",
    16: SWEEP_DIR / "embedding_16.yaml",
    64: SWEEP_DIR / "embedding_64.yaml",
}


def _without(mapping: dict, *keys: str) -> dict:
    return {key: value for key, value in mapping.items() if key not in keys}


def test_conventional_mlp_is_promoted_smaller_encoder_baseline() -> None:
    config = load_config(BASELINE)
    model = config["model"]

    assert model["site_embedding_dim"] == 32
    assert model["parallel_deep_hidden_units"] == [64, 32]
    assert model["deep_hidden_units"] == [64, 32]
    assert model["cross_layers"] == 0
    assert model["include_time_input_branch"] is True
    assert model["share_parallel_deep_net"] is True
    assert model["prediction_head_type"] == "multilabel"
    assert model["batch_size"] == 8192
    assert config["evaluation"]["benchmark_id"] == "xc-temporal-2024-jan-nov-v1"


def test_site_embedding_sweep_changes_only_embedding_hypothesis() -> None:
    baseline = load_config(BASELINE)

    for embedding_dim, path in CANDIDATES.items():
        candidate = load_config(path)

        assert candidate["task"] == baseline["task"]
        assert candidate["data"] == baseline["data"]
        assert candidate["evaluation"] == baseline["evaluation"]
        assert candidate["tracking"] == baseline["tracking"]
        assert candidate["model"]["site_embedding_dim"] == embedding_dim
        assert _without(candidate["model"], "name", "site_embedding_dim") == _without(
            baseline["model"], "name", "site_embedding_dim"
        )
        assert _without(candidate["artifact"], "output_dir") == _without(
            baseline["artifact"], "output_dir"
        )
        assert candidate["artifact"]["output_dir"].endswith(f"site-embedding/{embedding_dim}")
