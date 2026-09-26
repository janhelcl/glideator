import json

import pytest

from glideator_ml.s2s import run


def _config(output_dir):
    return {
        "task": "s2s",
        "data": {},
        "model": {"name": "deepsets", "seed": 42},
        "evaluation": {"benchmark_id": "s2s-v1"},
        "artifact": {
            "output_dir": str(output_dir),
            "filename": "model.pkl",
        },
        "tracking": {"enabled": True},
    }


def _report():
    return {
        "task": "s2s",
        "benchmark_id": "s2s-v1",
        "benchmark": {
            "split_strategy": "pilot",
            "split_seed": 42,
        },
        "dataset_fingerprint": "sha256:dataset",
        "eval_set_fingerprint": "sha256:evaluation",
        "model_seed": 42,
        "git_sha": "abc123",
        "model": {"model_type": "deepsets"},
        "metrics": {"hit_rate_at_5": 0.5},
    }


def test_backfill_tracks_saved_artifacts_and_persists_run_id(
    tmp_path,
    monkeypatch,
):
    report_path = tmp_path / "evaluation.json"
    report_path.write_text(json.dumps(_report()), encoding="utf-8")
    artifact_path = tmp_path / "model.pkl"
    artifact_path.write_bytes(b"model")
    captured = {}

    def fake_log_experiment(**kwargs):
        captured.update(kwargs)
        return "run-123"

    monkeypatch.setattr(run, "log_experiment", fake_log_experiment)

    result = run.backfill_s2s_tracking(_config(tmp_path))

    assert result["mlflow_run_id"] == "run-123"
    assert json.loads(report_path.read_text())["mlflow_run_id"] == "run-123"
    assert captured["metrics"] == {"hit_rate_at_5": 0.5}
    assert captured["tags"]["model_family"] == "deepsets"
    assert captured["artifacts"] == [artifact_path, report_path]


def test_backfill_is_idempotent(tmp_path, monkeypatch):
    report = _report()
    report["mlflow_run_id"] = "existing-run"
    (tmp_path / "evaluation.json").write_text(
        json.dumps(report),
        encoding="utf-8",
    )
    (tmp_path / "model.pkl").write_bytes(b"model")

    def unexpected_log_experiment(**kwargs):
        raise AssertionError("already tracked report must not be logged again")

    monkeypatch.setattr(run, "log_experiment", unexpected_log_experiment)

    result = run.backfill_s2s_tracking(_config(tmp_path))

    assert result["mlflow_run_id"] == "existing-run"


def test_backfill_requires_saved_artifact(tmp_path):
    (tmp_path / "evaluation.json").write_text(
        json.dumps(_report()),
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="model artifact"):
        run.backfill_s2s_tracking(_config(tmp_path))


def test_backfill_rejects_disabled_tracking(tmp_path, monkeypatch):
    (tmp_path / "evaluation.json").write_text(
        json.dumps(_report()),
        encoding="utf-8",
    )
    (tmp_path / "model.pkl").write_bytes(b"model")
    monkeypatch.setattr(run, "log_experiment", lambda **kwargs: None)

    with pytest.raises(RuntimeError, match="tracking is disabled"):
        run.backfill_s2s_tracking(_config(tmp_path))
