from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path) -> dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    required = {"task", "data", "model", "evaluation", "artifact", "tracking"}
    missing = sorted(required - config.keys())
    if missing:
        raise ValueError(f"Missing config sections: {', '.join(missing)}")
    return config


def flatten_config(value: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, item in value.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(item, dict):
            flat.update(flatten_config(item, name))
        elif isinstance(item, (list, tuple)):
            flat[name] = ",".join(str(part) for part in item)
        else:
            flat[name] = item
    return flat
