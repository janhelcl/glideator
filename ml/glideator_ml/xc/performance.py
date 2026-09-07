from __future__ import annotations

import copy
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import torch
from torch.utils.data import DataLoader

from .benchmark import split_temporal
from .data import fit_scaling_params, load_xc_data
from .model import ExpandedGlideatorNet, StandardScalerLayer
from .objective import xc_loss
from .preprocessing import TARGET_NAMES
from .selection import split_development
from .training import _dataset, _device, _features, _regularization, _seed_everything


@dataclass(frozen=True)
class BatchProfileResult:
    batch_size: int
    samples_per_second: float | None
    mean_step_ms: float | None
    estimated_epoch_seconds: float | None
    peak_allocated_gib: float | None
    peak_reserved_gib: float | None
    measured_steps: int
    measured_samples: int
    oom: bool
    error: str | None = None


def select_batch_size(
    results: Iterable[BatchProfileResult], *, throughput_fraction: float = 0.95
) -> int:
    """Choose the smallest batch size close to maximum measured throughput.

    Large batches can reduce optimization quality even after hardware throughput has
    saturated. The recommendation is therefore the smallest non-OOM batch reaching
    ``throughput_fraction`` of the best samples/second result.
    """

    if not 0 < throughput_fraction <= 1:
        raise ValueError("throughput_fraction must be in (0, 1]")
    valid = [
        result
        for result in results
        if not result.oom and result.samples_per_second is not None
    ]
    if not valid:
        raise RuntimeError("No batch size completed successfully")
    best_throughput = max(float(result.samples_per_second) for result in valid)
    cutoff = best_throughput * throughput_fraction
    return min(
        result.batch_size
        for result in valid
        if float(result.samples_per_second) >= cutoff
    )


def _build_model(train, features, config: dict[str, Any]) -> ExpandedGlideatorNet:
    weather_scaling, site_scaling = fit_scaling_params(train, features)
    requested_launches = config.get("num_launches")
    num_launches = int(requested_launches or (int(train["site_id"].max()) + 1))
    model_config = {
        "num_launches": num_launches,
        "num_targets": len(TARGET_NAMES),
        "deep_hidden_units": list(config.get("deep_hidden_units", [64, 32])),
        "cross_layers": int(config.get("cross_layers", 2)),
        "site_embedding_dim": int(config.get("site_embedding_dim", 8)),
        "prediction_head_type": str(config.get("prediction_head_type", "multilabel")),
        "parallel_deep_hidden_units": config.get("parallel_deep_hidden_units"),
        "share_cross_net": bool(config.get("share_cross_net", True)),
    }
    return ExpandedGlideatorNet(
        weather_scaler=StandardScalerLayer(weather_scaling),
        site_scaler=StandardScalerLayer(site_scaling),
        **model_config,
    )


def _next_batch(loader: DataLoader, iterator):
    try:
        return next(iterator), iterator
    except StopIteration:
        iterator = iter(loader)
        return next(iterator), iterator


def _sync(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def profile_batch_sizes(
    train,
    features,
    model_config: dict[str, Any],
    *,
    batch_sizes: Iterable[int],
    warmup_steps: int = 5,
    measured_steps: int = 20,
    throughput_fraction: float = 0.95,
) -> dict[str, Any]:
    """Measure actual XC training-step throughput for candidate batch sizes.

    This intentionally uses the same CPU TensorDataset -> device transfer path as the
    current trainer. If transfer optimization is added later, rerun the profile.
    """

    if warmup_steps < 0:
        raise ValueError("warmup_steps must be >= 0")
    if measured_steps <= 0:
        raise ValueError("measured_steps must be > 0")

    sizes = sorted({int(value) for value in batch_sizes})
    if not sizes or any(value <= 0 for value in sizes):
        raise ValueError("batch_sizes must contain positive integers")

    seed = int(model_config.get("seed", 42))
    deterministic = bool(model_config.get("deterministic", True))
    _seed_everything(seed, deterministic)
    device = _device(str(model_config.get("device", "auto")))
    if device.type != "cuda":
        raise RuntimeError(
            "XC batch profiling requires CUDA; set model.device=cuda on the GPU host"
        )

    dataset = _dataset(train, features)
    if len(dataset) < min(sizes):
        raise ValueError(
            f"Smallest batch size {min(sizes)} exceeds fit rows {len(dataset)}"
        )

    base_model = _build_model(train, features, model_config).cpu()
    base_state = copy.deepcopy(base_model.state_dict())
    learning_rate = float(model_config.get("learning_rate", 1e-3))
    monotonicity_lambda = float(model_config.get("monotonicity_lambda", 1e-9))
    l1_lambda = float(model_config.get("l1_lambda", 1e-9))
    l2_lambda = float(model_config.get("l2_lambda", 1e-9))
    num_workers = int(model_config.get("num_workers", 0))

    results: list[BatchProfileResult] = []
    for batch_size in sizes:
        if batch_size > len(dataset):
            results.append(
                BatchProfileResult(
                    batch_size=batch_size,
                    samples_per_second=None,
                    mean_step_ms=None,
                    estimated_epoch_seconds=None,
                    peak_allocated_gib=None,
                    peak_reserved_gib=None,
                    measured_steps=0,
                    measured_samples=0,
                    oom=False,
                    error=f"batch_size exceeds fit rows ({len(dataset)})",
                )
            )
            continue

        model = _build_model(train, features, model_config).to(device)
        model.load_state_dict(base_state)
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        generator = torch.Generator().manual_seed(seed)
        loader = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=True,
            generator=generator,
            num_workers=num_workers,
            drop_last=True,
        )
        iterator = iter(loader)

        try:
            for _ in range(warmup_steps):
                batch, iterator = _next_batch(loader, iterator)
                inputs, targets = _features(batch, device)
                optimizer.zero_grad(set_to_none=True)
                loss = xc_loss(
                    model(inputs),
                    targets,
                    monotonicity_lambda=monotonicity_lambda,
                )
                total = loss.total + _regularization(model, l1_lambda, l2_lambda)
                total.backward()
                optimizer.step()
            _sync(device)

            torch.cuda.reset_peak_memory_stats(device)
            start = time.perf_counter()
            samples = 0
            for _ in range(measured_steps):
                batch, iterator = _next_batch(loader, iterator)
                inputs, targets = _features(batch, device)
                optimizer.zero_grad(set_to_none=True)
                loss = xc_loss(
                    model(inputs),
                    targets,
                    monotonicity_lambda=monotonicity_lambda,
                )
                total = loss.total + _regularization(model, l1_lambda, l2_lambda)
                total.backward()
                optimizer.step()
                samples += int(targets.shape[0])
            _sync(device)
            elapsed = time.perf_counter() - start

            samples_per_second = samples / elapsed
            peak_allocated = torch.cuda.max_memory_allocated(device) / (1024**3)
            peak_reserved = torch.cuda.max_memory_reserved(device) / (1024**3)
            results.append(
                BatchProfileResult(
                    batch_size=batch_size,
                    samples_per_second=samples_per_second,
                    mean_step_ms=(elapsed / measured_steps) * 1000,
                    estimated_epoch_seconds=len(dataset) / samples_per_second,
                    peak_allocated_gib=peak_allocated,
                    peak_reserved_gib=peak_reserved,
                    measured_steps=measured_steps,
                    measured_samples=samples,
                    oom=False,
                )
            )
        except torch.OutOfMemoryError as exc:
            results.append(
                BatchProfileResult(
                    batch_size=batch_size,
                    samples_per_second=None,
                    mean_step_ms=None,
                    estimated_epoch_seconds=None,
                    peak_allocated_gib=None,
                    peak_reserved_gib=None,
                    measured_steps=0,
                    measured_samples=0,
                    oom=True,
                    error=str(exc),
                )
            )
        finally:
            del iterator, loader, optimizer, model
            torch.cuda.empty_cache()

    recommended = select_batch_size(
        results, throughput_fraction=throughput_fraction
    )
    successful = [result for result in results if result.samples_per_second is not None]
    best = max(successful, key=lambda result: float(result.samples_per_second))
    properties = torch.cuda.get_device_properties(device)

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "device": {
            "name": torch.cuda.get_device_name(device),
            "total_memory_gib": properties.total_memory / (1024**3),
            "compute_capability": f"{properties.major}.{properties.minor}",
        },
        "fit_rows": len(dataset),
        "warmup_steps": warmup_steps,
        "measured_steps": measured_steps,
        "throughput_fraction": throughput_fraction,
        "best_throughput_batch_size": best.batch_size,
        "recommended_batch_size": recommended,
        "recommendation_rule": (
            "smallest successful batch reaching the configured fraction of maximum "
            "samples/second"
        ),
        "results": [asdict(result) for result in results],
    }


def run_xc_batch_profile(
    config: dict[str, Any],
    *,
    batch_sizes: Iterable[int],
    warmup_steps: int = 5,
    measured_steps: int = 20,
    throughput_fraction: float = 0.95,
) -> dict[str, Any]:
    data_config = config["data"]
    frame, features = load_xc_data(data_config)
    split = split_temporal(
        frame,
        train_end=str(data_config["train_end"]),
        eval_start=str(data_config["eval_start"]),
        eval_end=str(data_config["eval_end"]),
        require_known_eval_sites=bool(data_config.get("require_known_eval_sites", True)),
    )
    validation_start = config["model"].get("validation_start")
    if validation_start is None:
        raise ValueError("model.validation_start is required for XC batch profiling")
    development = split_development(split.train, validation_start=validation_start)

    report = profile_batch_sizes(
        development.fit,
        features,
        config["model"],
        batch_sizes=batch_sizes,
        warmup_steps=warmup_steps,
        measured_steps=measured_steps,
        throughput_fraction=throughput_fraction,
    )
    output_dir = Path(config["artifact"].get("output_dir", "outputs/xc"))
    output_dir.mkdir(parents=True, exist_ok=True)
    profile_path = output_dir / "batch_profile.json"
    profile_path.write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    report["output_path"] = str(profile_path)
    return report
