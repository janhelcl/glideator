from __future__ import annotations

from pathlib import Path

import pytest

from glideator_ml.config import load_config, require_sections


def test_load_config_only_requires_task(tmp_path: Path) -> None:
    path = tmp_path / "reference.yaml"
    path.write_text("task: xc\nreference:\n  onnx_path: model.onnx\n", encoding="utf-8")

    config = load_config(path)

    assert config["task"] == "xc"
    assert "model" not in config


def test_require_sections_is_command_specific() -> None:
    config = {"task": "xc", "artifact": {}}

    require_sections(config, "artifact")
    with pytest.raises(ValueError, match="Missing config sections: model, tracking"):
        require_sections(config, "model", "artifact", "tracking")
