from __future__ import annotations

import asyncio
import hashlib
import json
import math
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from ..tracking import log_experiment
from .benchmark import (
    PRESSURE_LEVELS_HPA,
    XCFeatureContract,
    frame_fingerprint,
    split_temporal,
)
from .data import load_xc_data
from .evaluation import evaluate_predictions
from .preprocessing import TARGET_NAMES, WEATHER_TIMES, XC_THRESHOLDS
from .selection import split_development


JEV_MODEL_VERSION = "jev-1.13.0"
JEV_PROMPT_VERSION = "xc-semantic-weather-history-v1"
JEV_INPUT_PRICE_PER_BILLION_TOKENS_USD = 42.0


def _git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True) + "\n")
        handle.flush()


def _row_key(row: pd.Series) -> str:
    return f"{pd.Timestamp(row['date']).date()}|{int(row['site_id'])}"


def _rate_band(rate: float) -> str:
    if rate < 0.01:
        return "exceptionally rare"
    if rate < 0.05:
        return "very rare"
    if rate < 0.15:
        return "rare"
    if rate < 0.35:
        return "occasional"
    if rate < 0.60:
        return "common"
    return "very common"


def _rate_description(rate: float, observations: int) -> dict[str, Any]:
    return {
        "frequency": _rate_band(rate),
        "observed_rate_percent": round(100.0 * rate, 1),
        "fit_period_observations": int(observations),
    }


@dataclass(frozen=True)
class HistoricalPriors:
    global_rates: np.ndarray
    global_count: int
    site_rates: dict[int, np.ndarray]
    site_counts: dict[int, int]
    site_month_rates: dict[tuple[int, int], np.ndarray]
    site_month_counts: dict[tuple[int, int], int]

    def evidence(self, row: pd.Series, target_index: int) -> dict[str, Any]:
        site_id = int(row["site_id"])
        month = int(pd.Timestamp(row["date"]).month)
        site_rate = self.site_rates.get(site_id, self.global_rates)
        site_count = self.site_counts.get(site_id, self.global_count)
        site_month_key = (site_id, month)
        site_month_rate = self.site_month_rates.get(site_month_key, site_rate)
        site_month_count = self.site_month_counts.get(site_month_key, site_count)
        site_month = _rate_description(
            float(site_month_rate[target_index]), site_month_count
        )
        site_month["scope"] = (
            "same site and calendar month"
            if site_month_key in self.site_month_rates
            else "same-site fallback because that month is absent from fit data"
        )
        return {
            "same_site_same_month": site_month,
            "same_site_all_months": _rate_description(
                float(site_rate[target_index]), site_count
            ),
            "all_sites_all_months": _rate_description(
                float(self.global_rates[target_index]), self.global_count
            ),
            "provenance": "Computed only from fit rows before validation and evaluation.",
        }


def fit_historical_priors(
    fit: pd.DataFrame,
    *,
    smoothing_strength: float,
) -> HistoricalPriors:
    """Fit non-leaky empirical priors for question-specific Jev context."""

    if smoothing_strength < 0:
        raise ValueError("model.historical_prior_strength must be non-negative")
    targets = fit.loc[:, list(TARGET_NAMES)].to_numpy(dtype=float)
    global_rates = targets.mean(axis=0)
    global_count = len(fit)

    site_rates: dict[int, np.ndarray] = {}
    site_counts: dict[int, int] = {}
    for site_id, group in fit.groupby("site_id", sort=False):
        count = len(group)
        positives = group.loc[:, list(TARGET_NAMES)].sum(axis=0).to_numpy(dtype=float)
        rates = (positives + smoothing_strength * global_rates) / (
            count + smoothing_strength
        )
        site_rates[int(site_id)] = rates
        site_counts[int(site_id)] = count

    months = pd.to_datetime(fit["date"]).dt.month
    monthly = fit.assign(_month=months)
    site_month_rates: dict[tuple[int, int], np.ndarray] = {}
    site_month_counts: dict[tuple[int, int], int] = {}
    for (site_id, month), group in monthly.groupby(["site_id", "_month"], sort=False):
        key = (int(site_id), int(month))
        count = len(group)
        positives = group.loc[:, list(TARGET_NAMES)].sum(axis=0).to_numpy(dtype=float)
        parent = site_rates[int(site_id)]
        rates = (positives + smoothing_strength * parent) / (count + smoothing_strength)
        site_month_rates[key] = rates
        site_month_counts[key] = count

    return HistoricalPriors(
        global_rates=global_rates,
        global_count=global_count,
        site_rates=site_rates,
        site_counts=site_counts,
        site_month_rates=site_month_rates,
        site_month_counts=site_month_counts,
    )


def _feature(row: pd.Series, name: str, hour: int) -> float:
    return float(row[f"{name}_{hour}"])


def _wind_direction(u: float, v: float) -> str:
    # u/v describe motion toward east/north. Meteorological direction is where
    # the wind comes from.
    degrees = (math.degrees(math.atan2(-u, -v)) + 360.0) % 360.0
    names = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    return names[int((degrees + 22.5) // 45.0) % len(names)]


def _wind_band(speed: float) -> str:
    if speed < 2:
        return "calm"
    if speed < 5:
        return "light"
    if speed < 8:
        return "moderate"
    if speed < 12:
        return "strong"
    return "very strong"


def _humidity_band(value: float) -> str:
    if value < 35:
        return "dry"
    if value < 65:
        return "moderately humid"
    if value < 85:
        return "humid"
    return "near saturated"


def _lapse_band(value: float | None) -> str:
    if value is None:
        return "unavailable"
    if value < 4:
        return "very stable"
    if value < 6:
        return "stable"
    if value < 8:
        return "weakly unstable"
    return "strongly unstable"


def _cloud_base_band(height_m: float) -> str:
    if height_m < 500:
        return "very low"
    if height_m < 1000:
        return "low"
    if height_m < 1800:
        return "moderate"
    if height_m < 2800:
        return "high"
    return "very high"


def _precipitable_water_band(value: float) -> str:
    if value < 10:
        return "very dry column"
    if value < 20:
        return "dry column"
    if value < 35:
        return "moderately moist column"
    return "moist column"


def semantic_weather_snapshot(row: pd.Series, hour: int) -> dict[str, Any]:
    """Turn raw GFS numbers into compact concepts Jev can judge semantically."""

    altitude = float(row["altitude"])
    u10 = _feature(row, "u_wind_10m_ms", hour)
    v10 = _feature(row, "v_wind_10m_ms", hour)
    u100 = _feature(row, "u_wind_100m_ms", hour)
    v100 = _feature(row, "v_wind_100m_ms", hour)
    wind10 = math.hypot(u10, v10)
    wind100 = math.hypot(u100, v100)
    gust = _feature(row, "wind_gust_sfc_ms", hour)
    temperature_c = _feature(row, "temperature_2m_k", hour) - 273.15
    dewpoint_c = _feature(row, "dewpoint_2m_k", hour) - 273.15
    lcl_m = max(0.0, 125.0 * (temperature_c - dewpoint_c))

    profile: list[dict[str, float]] = []
    for level in PRESSURE_LEVELS_HPA:
        height_agl = _feature(row, f"geopotential_height_{level}hpa_m", hour) - altitude
        if 100 <= height_agl <= 3500:
            u = _feature(row, f"u_wind_{level}hpa_ms", hour)
            v = _feature(row, f"v_wind_{level}hpa_ms", hour)
            profile.append(
                {
                    "height_agl_m": height_agl,
                    "temperature_c": _feature(
                        row, f"temperature_{level}hpa_k", hour
                    )
                    - 273.15,
                    "relative_humidity_pct": _feature(
                        row, f"relative_humidity_{level}hpa_pct", hour
                    ),
                    "u": u,
                    "v": v,
                    "wind_speed": math.hypot(u, v),
                }
            )

    reference = min(profile, key=lambda item: abs(item["height_agl_m"] - 2000)) if profile else None
    lapse_rate = None
    if reference is not None and reference["height_agl_m"] >= 500:
        lapse_rate = (temperature_c - reference["temperature_c"]) / (
            reference["height_agl_m"] / 1000.0
        )

    flying_layer = [item for item in profile if item["height_agl_m"] <= 3000]
    layer_speeds = [wind100, *(item["wind_speed"] for item in flying_layer)]
    max_layer_wind = max(layer_speeds)
    low_humidity = [
        item["relative_humidity_pct"]
        for item in profile
        if item["height_agl_m"] <= 1500
    ]
    mid_humidity = [
        item["relative_humidity_pct"]
        for item in profile
        if 1500 < item["height_agl_m"] <= 3000
    ]
    low_rh = float(np.mean(low_humidity)) if low_humidity else float("nan")
    mid_rh = float(np.mean(mid_humidity)) if mid_humidity else float("nan")

    highest = max(flying_layer, key=lambda item: item["height_agl_m"]) if flying_layer else None
    return {
        "local_time": f"{hour:02d}:00",
        "surface_wind": {
            "description": f"{_wind_band(wind10)} from {_wind_direction(u10, v10)}",
            "speed_m_s": round(wind10, 1),
            "gust_m_s": round(gust, 1),
            "gust_description": _wind_band(gust),
        },
        "flying_layer_wind": {
            "description": _wind_band(max_layer_wind),
            "maximum_speed_below_3000m_agl_m_s": round(max_layer_wind, 1),
            "direction_near_100m": _wind_direction(u100, v100),
            "direction_near_layer_top": (
                _wind_direction(float(highest["u"]), float(highest["v"]))
                if highest is not None
                else _wind_direction(u100, v100)
            ),
        },
        "thermal_profile": {
            "description": _lapse_band(lapse_rate),
            "lapse_rate_c_per_km": (
                None if lapse_rate is None else round(lapse_rate, 1)
            ),
            "surface_temperature_c": round(temperature_c, 1),
        },
        "moisture": {
            "estimated_cloud_base_description": _cloud_base_band(lcl_m),
            "estimated_cloud_base_agl_m": round(lcl_m / 50.0) * 50,
            "low_level_humidity": (
                "unavailable" if math.isnan(low_rh) else _humidity_band(low_rh)
            ),
            "mid_level_humidity": (
                "unavailable" if math.isnan(mid_rh) else _humidity_band(mid_rh)
            ),
            "precipitable_water": _precipitable_water_band(
                _feature(row, "precipitable_water_clm_kg_m2", hour)
            ),
        },
    }


def build_jev_state(row: pd.Series) -> dict[str, Any]:
    date = pd.Timestamp(row["date"])
    month = int(date.month)
    if month in {12, 1, 2}:
        season = "winter"
    elif month in {3, 4, 5}:
        season = "spring"
    elif month in {6, 7, 8}:
        season = "summer"
    else:
        season = "autumn"
    return {
        "task_context": (
            "Forecast the maximum recorded paragliding XC result for one launch and day. "
            "The outcome depends on whether conditions are flyable, cross-country potential, "
            "and whether pilots are likely to fly and record a result."
        ),
        "site": {
            "site_id": str(int(row["site_id"])),
            "latitude": round(float(row["latitude"]), 3),
            "longitude": round(float(row["longitude"]), 3),
            "launch_altitude_m": round(float(row["altitude"])),
        },
        "calendar": {
            "month": date.month_name(),
            "season": season,
            "weekend": bool(date.weekday() >= 5),
        },
        "forecast": [semantic_weather_snapshot(row, hour) for hour in WEATHER_TIMES],
        "reading_note": (
            "Category labels are the primary evidence. Rounded measurements are supporting "
            "context; all meteorological arithmetic was performed before this request."
        ),
    }


def build_jev_questions(
    row: pd.Series,
    priors: HistoricalPriors,
) -> dict[str, dict[str, Any]]:
    questions: dict[str, dict[str, Any]] = {}
    for target_index, (target_name, threshold) in enumerate(
        zip(TARGET_NAMES, XC_THRESHOLDS, strict=True)
    ):
        questions[target_name] = {
            "type": "noul",
            "instructions": {
                "proposition": (
                    "At least one recorded paraglider flight launched at this site on this "
                    f"day will achieve strictly more than {threshold} XC points."
                ),
                "historical_evidence": priors.evidence(row, target_index),
                "decision_guidance": (
                    "Judge the proposition directly from the semantic forecast and historical "
                    "frequencies. Do not perform new meteorological arithmetic."
                ),
            },
            "criteria": {
                "true": f"The day's recorded maximum XC score is greater than {threshold}.",
                "false": f"The day's recorded maximum XC score is at most {threshold}.",
            },
        }
    return questions


def _cache_semantics(config: dict[str, Any]) -> dict[str, Any]:
    model = config["model"]
    return {
        "model_version": str(model.get("version", JEV_MODEL_VERSION)),
        "prompt_version": str(model.get("prompt_version", JEV_PROMPT_VERSION)),
        "historical_prior_strength": float(model.get("historical_prior_strength", 20.0)),
        "target_encoding": "independent-noul",
        "state_representation": "semantic-weather-v1",
    }


def _cache_fingerprint(manifest: dict[str, Any]) -> str:
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _load_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return records
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            key = str(record["row_key"])
            if key in records:
                raise ValueError(f"Duplicate Jev cache row {key!r} at line {line_number}")
            records[key] = record
    return records


class _StartRateLimiter:
    def __init__(self, requests_per_minute: float) -> None:
        if requests_per_minute <= 0:
            raise ValueError("model.requests_per_minute must be positive")
        self._interval = 60.0 / requests_per_minute
        self._next_start = 0.0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        async with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next_start - now)
            if delay:
                await asyncio.sleep(delay)
            started = time.monotonic()
            self._next_start = max(self._next_start, started) + self._interval


def _answer_probability(answer: Any) -> float:
    value = answer.get("noul") if isinstance(answer, dict) else getattr(answer, "noul")
    probability = float(value)
    if not 0.0 <= probability <= 1.0:
        raise ValueError(f"Jev returned invalid Noul probability {probability}")
    return probability


def _usage_value(usage: Any, name: str) -> int:
    value = usage.get(name) if isinstance(usage, dict) else getattr(usage, name, None)
    return 0 if value is None else int(value)


async def _call_jev(
    *,
    client: Any,
    row: pd.Series,
    priors: HistoricalPriors,
    requested_model: str,
    limiter: _StartRateLimiter,
) -> dict[str, Any]:
    await limiter.wait()
    started = time.perf_counter()
    response = await client.system_one(
        model=requested_model,
        state=build_jev_state(row),
        questions=build_jev_questions(row, priors),
    )
    latency = time.perf_counter() - started
    resolved_model = str(getattr(response, "model"))
    if resolved_model != requested_model:
        raise ValueError(
            f"Pinned Jev model {requested_model!r} resolved to {resolved_model!r}"
        )
    answers = getattr(response, "answers")
    probabilities = {
        target_name: _answer_probability(answers[target_name])
        for target_name in TARGET_NAMES
    }
    usage = getattr(response, "usage")
    return {
        "row_key": _row_key(row),
        "date": str(pd.Timestamp(row["date"]).date()),
        "site_id": int(row["site_id"]),
        "model": resolved_model,
        "probabilities": probabilities,
        "latency_seconds": latency,
        "input_tokens": _usage_value(usage, "input_tokens"),
        "output_tokens": _usage_value(usage, "output_tokens"),
    }


async def _predict_missing(
    *,
    rows: list[pd.Series],
    priors: HistoricalPriors,
    model_config: dict[str, Any],
    predictions_path: Path,
    failures_path: Path,
    client_factory: Callable[[dict[str, Any]], Any] | None,
) -> None:
    if not rows:
        return
    requested_model = str(model_config.get("version", JEV_MODEL_VERSION))
    concurrency = int(model_config.get("concurrency", 8))
    if concurrency <= 0:
        raise ValueError("model.concurrency must be positive")
    limiter = _StartRateLimiter(float(model_config.get("requests_per_minute", 900)))
    write_lock = asyncio.Lock()
    queue: asyncio.Queue[pd.Series | None] = asyncio.Queue()
    for row in rows:
        queue.put_nowait(row)
    for _ in range(min(concurrency, len(rows))):
        queue.put_nowait(None)

    if client_factory is None:
        try:
            from typesafe_sdk import AsyncTypeSafeClient, RetryPolicy
        except ImportError as exc:  # pragma: no cover - exercised without optional extra
            raise RuntimeError(
                "Jev benchmark dependencies are not installed. "
                "Install glideator-ml[jev,tracking]."
            ) from exc
        key_env = str(model_config.get("api_key_env", "TYPESAFE_API_KEY"))
        api_key = os.getenv(key_env)
        if not api_key:
            raise RuntimeError(f"Environment variable {key_env!r} is not set")
        retry = RetryPolicy(
            max_retries=int(model_config.get("max_retries", 5)),
            backoff_initial=float(model_config.get("backoff_initial_seconds", 0.5)),
            backoff_max=float(model_config.get("backoff_max_seconds", 30.0)),
        )
        client_context = AsyncTypeSafeClient(
            api_key=api_key,
            model=requested_model,
            retry=retry,
            timeout=float(model_config.get("timeout_seconds", 60.0)),
        )
    else:
        client_context = client_factory(model_config)

    async with client_context as client:

        async def worker() -> None:
            while True:
                row = await queue.get()
                if row is None:
                    queue.task_done()
                    return
                try:
                    record = await _call_jev(
                        client=client,
                        row=row,
                        priors=priors,
                        requested_model=requested_model,
                        limiter=limiter,
                    )
                    async with write_lock:
                        _append_jsonl(predictions_path, record)
                except Exception as exc:  # preserve progress; incomplete runs exit non-zero
                    async with write_lock:
                        _append_jsonl(
                            failures_path,
                            {
                                "row_key": _row_key(row),
                                "error_type": type(exc).__name__,
                                "error": str(exc),
                            },
                        )
                finally:
                    queue.task_done()

        workers = [
            asyncio.create_task(worker()) for _ in range(min(concurrency, len(rows)))
        ]
        await queue.join()
        await asyncio.gather(*workers)


def _tracking_tags(config: dict[str, Any], report: dict[str, Any]) -> dict[str, str]:
    benchmark = report["benchmark"]
    model = report["model"]
    return {
        "task": "xc",
        "model_family": "jev",
        "foundation_model": "jev",
        "foundation_model_version": str(model["version"]),
        "prompt_version": str(model["prompt_version"]),
        "target_encoding": "independent-noul",
        "hosted_model": "true",
        "benchmark_id": str(report["benchmark_id"]),
        "dataset_fingerprint": str(report["dataset_fingerprint"]),
        "eval_set_fingerprint": str(report["eval_set_fingerprint"]),
        "context_fingerprint": str(report["context_fingerprint"]),
        "git_sha": str(report["git_sha"]),
        "split_strategy": "temporal",
        "context_policy": str(report["selection"]["context_policy"]),
        "train_end": str(benchmark["train_end"]),
        "eval_start": str(benchmark["eval_start"]),
        "eval_end": str(benchmark["eval_end"]),
    }


def run_xc_jev(
    config: dict[str, Any],
    *,
    prepared_data: tuple[pd.DataFrame, XCFeatureContract] | None = None,
    limit: int | None = None,
    client_factory: Callable[[dict[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    """Benchmark pinned Jev probabilities on the canonical held-out XC rows.

    API responses are appended immediately and reused on subsequent runs. A partial
    smoke run can therefore be continued into the full benchmark without paying for
    the same evaluation row twice.
    """

    data_config = config["data"]
    model_config = config["model"]
    evaluation_config = config["evaluation"]
    if str(data_config.get("split_strategy", "temporal")) != "temporal":
        raise ValueError("The XC Jev benchmark supports only temporal splits")
    requested_model = str(model_config.get("version", JEV_MODEL_VERSION))
    if requested_model != JEV_MODEL_VERSION:
        raise ValueError(
            f"The checked-in Jev experiment is pinned to {JEV_MODEL_VERSION!r}; "
            f"got {requested_model!r}"
        )
    prompt_version = str(model_config.get("prompt_version", JEV_PROMPT_VERSION))
    if prompt_version != JEV_PROMPT_VERSION:
        raise ValueError(
            f"Unsupported Jev prompt version {prompt_version!r}; expected "
            f"{JEV_PROMPT_VERSION!r}"
        )
    if limit is not None and limit <= 0:
        raise ValueError("Jev smoke-run limit must be positive")

    frame, features = prepared_data or load_xc_data(data_config)
    dataset_fingerprint = frame_fingerprint(frame, features)
    benchmark = {
        "split_strategy": "temporal",
        "train_end": str(data_config["train_end"]),
        "eval_start": str(data_config["eval_start"]),
        "eval_end": str(data_config["eval_end"]),
    }
    split = split_temporal(
        frame,
        train_end=benchmark["train_end"],
        eval_start=benchmark["eval_start"],
        eval_end=benchmark["eval_end"],
        require_known_eval_sites=bool(data_config.get("require_known_eval_sites", True)),
        require_eval_boundary_coverage=bool(
            data_config.get("require_eval_boundary_coverage", False)
        ),
    )
    evaluation = split.evaluation.sort_values(["date", "site_id"], kind="mergesort").reset_index(
        drop=True
    )
    eval_fingerprint = frame_fingerprint(evaluation, features)

    validation_start = model_config.get("validation_start")
    if validation_start is None:
        raise ValueError("model.validation_start is required for Jev fit-period priors")
    development = split_development(split.train, validation_start=validation_start)
    context_policy = str(model_config.get("context_policy", "fit_parity"))
    if context_policy != "fit_parity":
        raise ValueError("The pinned Jev experiment requires model.context_policy=fit_parity")
    context = development.fit
    context_fingerprint = frame_fingerprint(context, features)
    priors = fit_historical_priors(
        context,
        smoothing_strength=float(model_config.get("historical_prior_strength", 20.0)),
    )

    output_dir = Path(config["artifact"].get("output_dir", "outputs/xc/baselines/jev-1.13"))
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "cache_manifest.json"
    predictions_path = output_dir / "predictions.jsonl"
    failures_path = output_dir / "failures.jsonl"
    manifest_payload = {
        "benchmark_id": str(
            evaluation_config.get("benchmark_id", "xc-temporal-2024-jan-nov-v1")
        ),
        "dataset_fingerprint": dataset_fingerprint,
        "eval_set_fingerprint": eval_fingerprint,
        "context_fingerprint": context_fingerprint,
        "feature_contract": features.as_dict(),
        "cache_semantics": _cache_semantics(config),
    }
    manifest = {
        **manifest_payload,
        "cache_fingerprint": _cache_fingerprint(manifest_payload),
    }
    if manifest_path.exists():
        existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if existing_manifest != manifest:
            raise ValueError(
                "Existing Jev cache does not match this dataset/model/prompt contract. "
                f"Move {output_dir} aside before starting a different experiment."
            )
    else:
        if predictions_path.exists():
            raise ValueError("Jev predictions cache exists without cache_manifest.json")
        _write_json(manifest_path, manifest)

    cached = _load_jsonl(predictions_path)
    if limit is None:
        scope = evaluation
    else:
        sample_size = min(limit, len(evaluation))
        sample_positions = np.linspace(
            0, len(evaluation) - 1, num=sample_size, dtype=int
        )
        scope = evaluation.iloc[sample_positions].reset_index(drop=True)
    pending_rows = [
        row
        for _, row in scope.iterrows()
        if _row_key(row) not in cached
    ]
    asyncio.run(
        _predict_missing(
            rows=pending_rows,
            priors=priors,
            model_config=model_config,
            predictions_path=predictions_path,
            failures_path=failures_path,
            client_factory=client_factory,
        )
    )

    cached = _load_jsonl(predictions_path)
    successful_indices = [
        index for index, row in scope.iterrows() if _row_key(row) in cached
    ]
    missing_keys = [
        _row_key(row) for _, row in scope.iterrows() if _row_key(row) not in cached
    ]
    if not successful_indices:
        raise RuntimeError(
            f"Jev produced no usable predictions; inspect {failures_path}"
        )
    evaluated = scope.iloc[successful_indices]
    probabilities = np.asarray(
        [
            [cached[_row_key(row)]["probabilities"][name] for name in TARGET_NAMES]
            for _, row in evaluated.iterrows()
        ],
        dtype=float,
    )
    targets = evaluated.loc[:, list(TARGET_NAMES)].to_numpy(dtype=float)
    metrics = evaluate_predictions(targets, probabilities)
    records = [cached[_row_key(row)] for _, row in evaluated.iterrows()]
    latencies = np.asarray([record["latency_seconds"] for record in records], dtype=float)
    input_tokens = sum(int(record["input_tokens"]) for record in records)
    output_tokens = sum(int(record["output_tokens"]) for record in records)
    metrics.update(
        {
            "dataset_rows": len(frame),
            "development_rows": len(split.train),
            "fit_rows": len(context),
            "validation_rows": len(development.validation),
            "eval_rows": len(evaluation),
            "evaluated_rows": len(evaluated),
            "missing_rows_in_scope": len(missing_keys),
            "api_requests": len(records),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_input_cost_usd": (
                input_tokens * JEV_INPUT_PRICE_PER_BILLION_TOKENS_USD / 1_000_000_000
            ),
            "estimated_full_input_cost_usd": (
                (input_tokens / len(evaluated))
                * len(evaluation)
                * JEV_INPUT_PRICE_PER_BILLION_TOKENS_USD
                / 1_000_000_000
            ),
            "estimated_full_minimum_minutes_at_configured_rate": (
                len(evaluation)
                / float(model_config.get("requests_per_minute", 900))
            ),
            "latency_seconds_mean": float(latencies.mean()),
            "latency_seconds_p50": float(np.quantile(latencies, 0.50)),
            "latency_seconds_p95": float(np.quantile(latencies, 0.95)),
        }
    )

    complete = limit is None and not missing_keys and len(evaluated) == len(evaluation)
    benchmark_id = str(
        evaluation_config.get("benchmark_id", "xc-temporal-2024-jan-nov-v1")
    )
    report: dict[str, Any] = {
        "task": "xc",
        "benchmark_id": benchmark_id,
        "dataset_fingerprint": dataset_fingerprint,
        "eval_set_fingerprint": eval_fingerprint,
        "context_fingerprint": context_fingerprint,
        "git_sha": _git_sha(),
        "benchmark": benchmark,
        "selection": {
            "validation_start": str(validation_start),
            "context_policy": context_policy,
        },
        "feature_contract": features.as_dict(),
        "model": {
            "name": str(model_config.get("name", "xc-jev-1.13")),
            "family": "jev",
            "version": requested_model,
            "sdk_version": "0.7.0",
            "prompt_version": prompt_version,
            "target_encoding": "independent-noul",
            "historical_prior_strength": float(
                model_config.get("historical_prior_strength", 20.0)
            ),
            "hosted": True,
        },
        "run_scope": {
            "limit": limit,
            "complete": complete,
            "successful_rows": len(evaluated),
            "missing_rows": len(missing_keys),
            "missing_row_keys_sample": missing_keys[:20],
        },
        "metrics": metrics,
    }
    report_path = output_dir / ("evaluation.json" if complete else "evaluation.partial.json")
    _write_json(report_path, report)

    run_id = None
    if complete:
        artifacts = [report_path, manifest_path, predictions_path]
        if failures_path.exists():
            artifacts.append(failures_path)
        run_id = log_experiment(
            config=config,
            metrics=metrics,
            tags=_tracking_tags(config, report),
            artifacts=artifacts,
        )
        report["mlflow_run_id"] = run_id
        if run_id is not None:
            _write_json(report_path, report)
    else:
        report["mlflow_run_id"] = None
    return report
