from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from glideator_ml.cli import build_parser
from glideator_ml.xc import seed_comparison


def _config(name: str, output_dir: Path) -> dict:
    return {
        "task": "xc",
        "data": {
            "source": "database",
            "table": "features",
            "train_end": "2023-12-31",
            "eval_start": "2024-01-01",
            "eval_end": "2024-11-30",
        },
        "model": {"name": name, "seed": 42},
        "evaluation": {"benchmark_id": "xc-test-v1", "batch_size": 32},
        "artifact": {"output_dir": str(output_dir), "filename": "model.pt"},
        "tracking": {"enabled": False},
    }


def test_seeded_config_isolates_seed_artifacts_without_mutating_source(tmp_path: Path) -> None:
    config = _config("candidate", tmp_path / "candidate")
    original = copy.deepcopy(config)

    seeded = seed_comparison._seeded_config(config, 44)

    assert config == original
    assert seeded["model"]["seed"] == 44
    assert seeded["model"]["name"] == "candidate-seed-44"
    assert seeded["artifact"]["output_dir"].endswith("seed-sweep/seed-44")


def test_seed_comparison_runs_paired_seeds_on_one_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    control = _config("control", tmp_path / "control")
    candidate = _config("candidate", tmp_path / "candidate")
    prepared = (object(), object())
    load_calls = 0
    run_calls: list[tuple[str, int]] = []

    def fake_load_xc_data(data_config):
        nonlocal load_calls
        assert data_config == candidate["data"]
        load_calls += 1
        return prepared

    def fake_run_xc(config, *, prepared_data=None):
        assert prepared_data is prepared
        seed = int(config["model"]["seed"])
        name = str(config["model"]["name"])
        is_candidate = name.startswith("candidate")
        run_calls.append(("candidate" if is_candidate else "control", seed))
        return {
            "benchmark_id": "xc-test-v1",
            "dataset_fingerprint": "dataset-1",
            "eval_set_fingerprint": "eval-1",
            "model_seed": seed,
            "mlflow_run_id": f"run-{name}",
            "metrics": {
                "bce_macro": 0.15 if is_candidate else 0.16,
                "brier_macro": 0.049 if is_candidate else 0.050,
                "roc_auc_macro": 0.941 if is_candidate else 0.940,
                "monotonic_violation_rate": 0.021 if is_candidate else 0.020,
                "best_epoch": seed,
                "trainable_parameters": 48_000 if is_candidate else 64_000,
            },
        }

    monkeypatch.setattr(seed_comparison, "load_xc_data", fake_load_xc_data)
    monkeypatch.setattr(seed_comparison, "run_xc", fake_run_xc)

    report = seed_comparison.run_xc_seed_comparison(
        control, candidate, seeds=[42, 43]
    )

    assert load_calls == 1
    assert run_calls == [
        ("candidate", 42),
        ("control", 42),
        ("candidate", 43),
        ("control", 43),
    ]
    assert report["seeds"] == [42, 43]
    assert report["summary"]["bce_macro"]["candidate_wins"] == 2
    assert report["summary"]["roc_auc_macro"]["candidate_wins"] == 2
    assert report["summary"]["monotonic_violation_rate"]["candidate_wins"] == 0
    assert report["summary"]["bce_macro"][
        "mean_delta_candidate_minus_control"
    ] == pytest.approx(-0.01)

    summary_path = Path(report["summary_path"])
    assert summary_path.is_file()
    saved = json.loads(summary_path.read_text(encoding="utf-8"))
    assert saved["comparison"] == "paired_seed_confirmation"
    assert saved["summary"]["brier_macro"]["candidate_wins"] == 2


def test_multi_control_confirmation_reuses_candidate_per_seed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    mlp = _config("mlp", tmp_path / "mlp")
    cnn = _config("cnn", tmp_path / "cnn")
    candidate = _config("agl", tmp_path / "agl")
    prepared = (object(), object())
    run_calls: list[tuple[str, int]] = []

    monkeypatch.setattr(
        seed_comparison,
        "load_xc_data",
        lambda data_config: prepared,
    )

    def fake_run_xc(config, *, prepared_data=None):
        assert prepared_data is prepared
        seed = int(config["model"]["seed"])
        seeded_name = str(config["model"]["name"])
        name = seeded_name.split("-seed-")[0]
        run_calls.append((name, seed))
        offsets = {"mlp": 0.010, "cnn": 0.005, "agl": 0.000}
        offset = offsets[name]
        return {
            "benchmark_id": "xc-test-v1",
            "dataset_fingerprint": "dataset-1",
            "eval_set_fingerprint": "eval-1",
            "model_seed": seed,
            "mlflow_run_id": f"run-{seeded_name}",
            "metrics": {
                "bce_macro": 0.15 + offset,
                "brier_macro": 0.049 + offset,
                "roc_auc_macro": 0.941 - offset,
                "monotonic_violation_rate": 0.020 + offset,
                "best_epoch": seed,
                "trainable_parameters": 58_000,
            },
        }

    monkeypatch.setattr(seed_comparison, "run_xc", fake_run_xc)

    report = seed_comparison.run_xc_seed_comparisons(
        [mlp, cnn], candidate, seeds=[42, 43]
    )

    assert run_calls == [
        ("agl", 42),
        ("mlp", 42),
        ("cnn", 42),
        ("agl", 43),
        ("mlp", 43),
        ("cnn", 43),
    ]
    assert report["control_models"] == ["mlp", "cnn"]
    assert report["candidate_model"] == "agl"
    assert len(report["comparisons"]) == 2
    for comparison in report["comparisons"]:
        assert comparison["summary"]["bce_macro"]["candidate_wins"] == 2
        assert comparison["summary"]["roc_auc_macro"]["candidate_wins"] == 2
        candidate_run_ids = [
            pair["candidate"]["mlflow_run_id"] for pair in comparison["pairs"]
        ]
        assert candidate_run_ids == ["run-agl-seed-42", "run-agl-seed-43"]

    summary_path = Path(report["summary_path"])
    assert summary_path.name == "paired_comparisons.json"
    saved = json.loads(summary_path.read_text(encoding="utf-8"))
    assert saved["comparison"] == "paired_seed_confirmation_multi_control"


def test_confirm_seeds_cli_accepts_multiple_controls() -> None:
    args = build_parser().parse_args(
        [
            "confirm-seeds",
            "xc",
            "--config",
            "candidate.yaml",
            "--control-config",
            "mlp.yaml",
            "cnn.yaml",
            "--seeds",
            "42",
            "43",
        ]
    )

    assert args.control_config == ["mlp.yaml", "cnn.yaml"]
    assert args.seeds == [42, 43]


def test_seed_comparison_rejects_mismatched_benchmark_contract(tmp_path: Path) -> None:
    control = _config("control", tmp_path / "control")
    candidate = _config("candidate", tmp_path / "candidate")
    candidate["evaluation"]["benchmark_id"] = "different"

    with pytest.raises(ValueError, match="identical evaluation configs"):
        seed_comparison.run_xc_seed_comparison(control, candidate, seeds=[42])


def test_seed_comparison_rejects_duplicate_seeds(tmp_path: Path) -> None:
    control = _config("control", tmp_path / "control")
    candidate = _config("candidate", tmp_path / "candidate")

    with pytest.raises(ValueError, match="seeds must be unique"):
        seed_comparison.run_xc_seed_comparison(control, candidate, seeds=[42, 42])


def test_multi_control_confirmation_requires_unique_control_names(tmp_path: Path) -> None:
    control_a = _config("control", tmp_path / "control-a")
    control_b = _config("control", tmp_path / "control-b")
    candidate = _config("candidate", tmp_path / "candidate")

    with pytest.raises(ValueError, match="control model names must be unique"):
        seed_comparison.run_xc_seed_comparisons(
            [control_a, control_b], candidate, seeds=[42]
        )
