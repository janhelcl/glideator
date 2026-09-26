from __future__ import annotations

from pathlib import Path

from glideator_ml.config import load_config


CONFIG_DIR = (
    Path(__file__).parents[1] / "configs" / "xc" / "architecture" / "refinement"
)
CONFIG_NAMES = (
    "control",
    "no_raw_skip",
    "time_specific_encoder",
    "smaller_encoder",
    "larger_encoder",
    "smaller_fusion",
    "deeper_fusion",
)


def test_refinement_configs_share_benchmark_and_training_contract() -> None:
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
        "site_embedding_dim",
        "cross_layers",
        "prediction_head_type",
        "share_cross_net",
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
        assert config["evaluation"] == control["evaluation"], name
        assert config["evaluation"]["benchmark_id"] == "xc-temporal-2024-jan-nov-v1"
        assert config["artifact"]["export_onnx"] is False
        assert config["artifact"]["output_dir"].endswith(name.replace("_", "-"))
        for key in invariant_data:
            assert config["data"][key] == control["data"][key], (name, key)
        for key in invariant_model:
            assert config["model"][key] == control["model"][key], (name, key)


def test_refinement_variants_change_one_structural_hypothesis() -> None:
    configs = {name: load_config(CONFIG_DIR / f"{name}.yaml") for name in CONFIG_NAMES}
    control = configs["control"]["model"]

    assert configs["no_raw_skip"]["model"]["include_time_input_branch"] is False
    assert configs["no_raw_skip"]["model"]["parallel_deep_hidden_units"] == control[
        "parallel_deep_hidden_units"
    ]

    assert configs["time_specific_encoder"]["model"]["share_parallel_deep_net"] is False
    assert configs["time_specific_encoder"]["model"]["parallel_deep_hidden_units"] == control[
        "parallel_deep_hidden_units"
    ]

    assert configs["smaller_encoder"]["model"]["parallel_deep_hidden_units"] == [64, 32]
    assert configs["larger_encoder"]["model"]["parallel_deep_hidden_units"] == [
        256,
        128,
        64,
    ]
    assert configs["smaller_fusion"]["model"]["deep_hidden_units"] == [32, 16]
    assert configs["deeper_fusion"]["model"]["deep_hidden_units"] == [64, 64, 32]

    for name in ("smaller_encoder", "larger_encoder"):
        assert configs[name]["model"]["deep_hidden_units"] == control["deep_hidden_units"]
    for name in ("smaller_fusion", "deeper_fusion"):
        assert configs[name]["model"]["parallel_deep_hidden_units"] == control[
            "parallel_deep_hidden_units"
        ]
