from __future__ import annotations

from pathlib import Path

from glideator_ml.config import load_config


ROOT = Path(__file__).parents[1]
BASELINE = ROOT / "configs" / "xc" / "baselines" / "conventional_mlp.yaml"
SWEEP_DIR = ROOT / "configs" / "xc" / "optimization" / "training"

CONTROL = SWEEP_DIR / "control.yaml"
CANDIDATES = {
    "lr_5e4": (SWEEP_DIR / "lr_5e-4.yaml", {"learning_rate": 0.0005}),
    "lr_2e3": (SWEEP_DIR / "lr_2e-3.yaml", {"learning_rate": 0.002}),
    "lr_3e3": (SWEEP_DIR / "lr_3e-3.yaml", {"learning_rate": 0.003}),
    "l2_1e7": (SWEEP_DIR / "l2_1e-7.yaml", {"l2_lambda": 1.0e-7}),
    "l2_1e6": (SWEEP_DIR / "l2_1e-6.yaml", {"l2_lambda": 1.0e-6}),
    "dropout_005": (SWEEP_DIR / "dropout_005.yaml", {"dropout": 0.05}),
    "dropout_010": (SWEEP_DIR / "dropout_010.yaml", {"dropout": 0.10}),
}


def _without(mapping: dict, *keys: str) -> dict:
    return {key: value for key, value in mapping.items() if key not in keys}


def test_training_control_matches_conventional_baseline() -> None:
    baseline = load_config(BASELINE)
    control = load_config(CONTROL)
    baseline_model = {**baseline["model"], "dropout": 0.0}

    assert control["task"] == baseline["task"]
    assert control["data"] == baseline["data"]
    assert control["evaluation"] == baseline["evaluation"]
    assert control["tracking"] == baseline["tracking"]
    assert _without(control["model"], "name") == _without(baseline_model, "name")
    assert _without(control["artifact"], "output_dir") == _without(
        baseline["artifact"], "output_dir"
    )


def test_training_optimization_configs_change_one_axis_at_a_time() -> None:
    control = load_config(CONTROL)

    for path, overrides in CANDIDATES.values():
        candidate = load_config(path)

        assert candidate["task"] == control["task"]
        assert candidate["data"] == control["data"]
        assert candidate["evaluation"] == control["evaluation"]
        assert candidate["tracking"] == control["tracking"]

        changed_keys = {"name", *overrides}
        assert _without(candidate["model"], *changed_keys) == _without(
            control["model"], *changed_keys
        )
        for key, value in overrides.items():
            assert candidate["model"][key] == value

        assert _without(candidate["artifact"], "output_dir") == _without(
            control["artifact"], "output_dir"
        )
        assert candidate["artifact"]["output_dir"].startswith(
            "outputs/xc/optimization/training/"
        )
