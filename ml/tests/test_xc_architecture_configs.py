from __future__ import annotations

from pathlib import Path

from glideator_ml.config import load_config


CONFIG_DIR = Path(__file__).parents[1] / "configs" / "xc" / "architecture"
CONFIG_NAMES = (
    "control",
    "ordinal",
    "no_parallel",
    "no_cross",
    "time_specific_cross",
    "wider_fusion",
)


def test_xc_architecture_sweep_configs_share_training_contract() -> None:
    configs = {name: load_config(CONFIG_DIR / f"{name}.yaml") for name in CONFIG_NAMES}
    control = configs["control"]

    invariant_data = (
        "start_date",
        "max_site_id",
        "split_strategy",
        "train_end",
        "eval_start",
        "eval_end",
        "require_known_eval_sites",
        "require_eval_boundary_coverage",
        "site_features",
    )
    invariant_model = (
        "seed",
        "deterministic",
        "device",
        "validation_start",
        "num_launches",
        "batch_size",
        "num_workers",
        "learning_rate",
        "lr_decay",
        "epochs",
        "patience",
        "l1_lambda",
        "l2_lambda",
        "monotonicity_lambda",
    )

    for name, config in configs.items():
        assert config["task"] == "xc", name
        assert config["evaluation"]["benchmark_id"] == "xc-temporal-2024-jan-nov-v1"
        assert config["model"]["batch_size"] == 8192
        assert config["model"]["patience"] == 40
        assert config["artifact"]["export_onnx"] is False
        for key in invariant_data:
            assert config["data"][key] == control["data"][key], (name, key)
        for key in invariant_model:
            assert config["model"][key] == control["model"][key], (name, key)


def test_xc_architecture_sweep_changes_one_structural_hypothesis_per_variant() -> None:
    configs = {name: load_config(CONFIG_DIR / f"{name}.yaml") for name in CONFIG_NAMES}
    control = configs["control"]["model"]

    assert configs["ordinal"]["model"]["prediction_head_type"] == "ordinal"
    assert configs["ordinal"]["model"]["deep_hidden_units"] == control["deep_hidden_units"]

    assert configs["no_parallel"]["model"]["parallel_deep_hidden_units"] is None
    assert configs["no_parallel"]["model"]["cross_layers"] == control["cross_layers"]

    assert configs["no_cross"]["model"]["cross_layers"] == 0
    assert configs["no_cross"]["model"]["parallel_deep_hidden_units"] == control[
        "parallel_deep_hidden_units"
    ]

    assert configs["time_specific_cross"]["model"]["share_cross_net"] is False
    assert configs["time_specific_cross"]["model"]["cross_layers"] == control[
        "cross_layers"
    ]

    assert configs["wider_fusion"]["model"]["deep_hidden_units"] == [128, 64]
    assert configs["wider_fusion"]["model"]["parallel_deep_hidden_units"] == control[
        "parallel_deep_hidden_units"
    ]
