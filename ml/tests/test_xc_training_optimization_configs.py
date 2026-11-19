from __future__ import annotations

from pathlib import Path

from glideator_ml.config import load_config


ROOT = Path(__file__).parents[1]
BASELINE = ROOT / "configs" / "xc" / "baselines" / "conventional_mlp.yaml"
SWEEP_DIR = ROOT / "configs" / "xc" / "optimization" / "training"

CONTROL = SWEEP_DIR / "control.yaml"
SCREEN_CANDIDATES = {
    "lr_5e4": (SWEEP_DIR / "lr_5e-4.yaml", {"learning_rate": 0.0005}),
    "lr_2e3": (SWEEP_DIR / "lr_2e-3.yaml", {"learning_rate": 0.002}),
    "lr_3e3": (SWEEP_DIR / "lr_3e-3.yaml", {"learning_rate": 0.003}),
    "l2_1e7": (SWEEP_DIR / "l2_1e-7.yaml", {"l2_lambda": 1.0e-7}),
    "l2_1e6": (SWEEP_DIR / "l2_1e-6.yaml", {"l2_lambda": 1.0e-6}),
    "dropout_005": (SWEEP_DIR / "dropout_005.yaml", {"dropout": 0.05}),
    "dropout_010": (SWEEP_DIR / "dropout_010.yaml", {"dropout": 0.10}),
}

FOLLOW_UP_CONTROL = SWEEP_DIR / "dropout_010.yaml"
FOLLOW_UP_CANDIDATES = {
    "dropout_0075": (SWEEP_DIR / "dropout_0075.yaml", {"dropout": 0.075}),
    "dropout_0125": (SWEEP_DIR / "dropout_0125.yaml", {"dropout": 0.125}),
    "dropout_015": (SWEEP_DIR / "dropout_015.yaml", {"dropout": 0.15}),
    "dropout_010_l2_1e6": (
        SWEEP_DIR / "dropout_010_l2_1e-6.yaml",
        {"l2_lambda": 1.0e-6},
    ),
    "dropout_010_lr_2e3": (
        SWEEP_DIR / "dropout_010_lr_2e-3.yaml",
        {"learning_rate": 0.002},
    ),
}


def _without(mapping: dict, *keys: str) -> dict:
    return {key: value for key, value in mapping.items() if key not in keys}


def _assert_same_experiment_contract(candidate: dict, control: dict) -> None:
    assert candidate["task"] == control["task"]
    assert candidate["data"] == control["data"]
    assert candidate["evaluation"] == control["evaluation"]
    assert candidate["tracking"] == control["tracking"]
    assert _without(candidate["artifact"], "output_dir") == _without(
        control["artifact"], "output_dir"
    )
    assert candidate["artifact"]["output_dir"].startswith(
        "outputs/xc/optimization/training/"
    )


def _assert_model_overrides(candidate: dict, control: dict, overrides: dict) -> None:
    changed_keys = {"name", *overrides}
    assert _without(candidate["model"], *changed_keys) == _without(
        control["model"], *changed_keys
    )
    for key, value in overrides.items():
        assert candidate["model"][key] == value


def test_historical_training_control_matches_frozen_baseline_except_dropout() -> None:
    baseline = load_config(BASELINE)
    control = load_config(CONTROL)

    assert baseline["model"]["dropout"] == 0.10
    assert control["model"].get("dropout", 0.0) == 0.0
    assert control["task"] == baseline["task"]
    assert control["data"] == baseline["data"]
    assert control["evaluation"] == baseline["evaluation"]
    assert control["tracking"] == baseline["tracking"]
    assert _without(control["model"], "name", "dropout") == _without(
        baseline["model"], "name", "dropout"
    )
    assert _without(control["artifact"], "output_dir") == _without(
        baseline["artifact"], "output_dir"
    )


def test_training_screen_configs_change_one_axis_at_a_time() -> None:
    control = load_config(CONTROL)

    for path, overrides in SCREEN_CANDIDATES.values():
        candidate = load_config(path)
        _assert_same_experiment_contract(candidate, control)
        _assert_model_overrides(candidate, control, overrides)


def test_training_follow_up_configs_are_local_to_dropout_winner() -> None:
    control = load_config(FOLLOW_UP_CONTROL)
    assert control["model"]["dropout"] == 0.10

    for path, overrides in FOLLOW_UP_CANDIDATES.values():
        candidate = load_config(path)
        _assert_same_experiment_contract(candidate, control)
        _assert_model_overrides(candidate, control, overrides)
