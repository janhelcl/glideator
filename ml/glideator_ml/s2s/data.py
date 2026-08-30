from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass

import pandas as pd
from sqlalchemy import create_engine, text


@dataclass(frozen=True)
class S2SSplit:
    train_visits: pd.DataFrame
    eval_visits: pd.DataFrame


def _database_url(config: dict) -> str:
    env_name = config.get("database_url_env", "ML_DATABASE_URL")
    value = os.getenv(env_name)
    if not value:
        raise RuntimeError(
            f"Database source selected but environment variable {env_name!r} is not set"
        )
    return value


def load_visits(config: dict) -> pd.DataFrame:
    source = config.get("source", "database")
    if source == "csv":
        path = config.get("path")
        if not path:
            raise ValueError("data.path is required when data.source=csv")
        raw = pd.read_csv(path)
    elif source == "database":
        engine = create_engine(_database_url(config))
        schema = str(config.get("schema", "mart"))
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", schema):
            raise ValueError(f"Invalid database schema: {schema!r}")
        query = text(
            f"""
            select
                f.pilot,
                s.site_id,
                f.date,
                f.start_time
            from {schema}.fact_flights f
            join {schema}.dim_sites s
              on f.site = s.xc_name
            where f.pilot is not null
              and s.site_id is not null
            """
        )
        with engine.connect() as connection:
            raw = pd.read_sql(query, connection)
    else:
        raise ValueError(f"Unsupported S2S data source: {source!r}")

    return first_visits(raw)


def first_visits(raw: pd.DataFrame) -> pd.DataFrame:
    required = {"pilot", "site_id", "date"}
    missing = required - set(raw.columns)
    if missing:
        raise ValueError(f"Missing S2S input columns: {', '.join(sorted(missing))}")

    frame = raw.copy()
    frame = frame.dropna(subset=["pilot", "site_id", "date"])
    frame["pilot"] = frame["pilot"].astype(str)
    frame["site_id"] = frame["site_id"].astype(int)

    date_text = frame["date"].astype(str)
    if "start_time" in frame:
        timestamp = pd.to_datetime(
            date_text + " " + frame["start_time"].fillna("").astype(str),
            errors="coerce",
        )
    else:
        timestamp = pd.to_datetime(date_text, errors="coerce")
    fallback = pd.to_datetime(frame["date"], errors="coerce")
    frame["visit_at"] = timestamp.fillna(fallback)
    frame = frame.dropna(subset=["visit_at"])

    frame = frame.sort_values(
        ["pilot", "visit_at", "site_id"], kind="mergesort"
    ).drop_duplicates(["pilot", "site_id"], keep="first")

    return frame[["pilot", "site_id", "visit_at"]].reset_index(drop=True)


def _bucket(pilot: str, seed: int) -> float:
    digest = hashlib.sha256(f"{seed}:{pilot}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def split_pilots(
    visits: pd.DataFrame,
    *,
    eval_fraction: float,
    seed: int,
) -> S2SSplit:
    if not 0.0 < eval_fraction < 1.0:
        raise ValueError("eval_fraction must be between 0 and 1")

    pilots = sorted(visits["pilot"].unique())
    eval_pilots = {
        pilot for pilot in pilots if _bucket(str(pilot), seed) < eval_fraction
    }

    # Extremely small synthetic datasets can hash entirely to one side.
    if pilots and not eval_pilots:
        eval_pilots.add(pilots[-1])
    if len(eval_pilots) == len(pilots) and len(pilots) > 1:
        eval_pilots.remove(pilots[0])

    mask = visits["pilot"].isin(eval_pilots)
    return S2SSplit(
        train_visits=visits.loc[~mask].reset_index(drop=True),
        eval_visits=visits.loc[mask].reset_index(drop=True),
    )


def _as_cutoff(value: str) -> pd.Timestamp:
    cutoff = pd.Timestamp(value)
    if pd.isna(cutoff):
        raise ValueError(f"Invalid temporal cutoff: {value!r}")
    if cutoff.tzinfo is not None:
        cutoff = cutoff.tz_localize(None)
    return cutoff


def split_temporal(
    visits: pd.DataFrame,
    *,
    cutoff: str,
) -> S2SSplit:
    """Split by information availability at a fixed point in time.

    Training contains only first visits known before the cutoff. eval_visits is
    the post-cutoff portion and is used for reporting; temporal walk-forward
    events are built from the full visit history so legitimate pre-cutoff source
    history is retained.
    """
    cutoff_at = _as_cutoff(cutoff)
    mask = visits["visit_at"] < cutoff_at
    train_visits = visits.loc[mask].reset_index(drop=True)
    eval_visits = visits.loc[~mask].reset_index(drop=True)
    if train_visits.empty:
        raise ValueError("Temporal S2S split produced an empty training set")
    if eval_visits.empty:
        raise ValueError("Temporal S2S split produced an empty evaluation set")
    return S2SSplit(train_visits=train_visits, eval_visits=eval_visits)


def walk_forward_events(
    eval_visits: pd.DataFrame,
    *,
    min_history: int = 1,
) -> list[tuple[str, tuple[int, ...], int]]:
    events: list[tuple[str, tuple[int, ...], int]] = []
    ordered = eval_visits.sort_values(["pilot", "visit_at", "site_id"], kind="mergesort")
    for pilot, group in ordered.groupby("pilot", sort=True):
        sites = group["site_id"].astype(int).tolist()
        for index in range(min_history, len(sites)):
            events.append((str(pilot), tuple(sites[:index]), sites[index]))
    return events


def temporal_walk_forward_events(
    visits: pd.DataFrame,
    *,
    cutoff: str,
    min_history: int = 1,
) -> list[tuple[str, tuple[int, ...], int]]:
    """Build post-cutoff targets with only history available before each target.

    Unlike applying walk_forward_events to the post-cutoff rows alone, this
    preserves sites a pilot had already discovered before the cutoff. Later
    post-cutoff first visits become valid history for subsequent targets, which
    matches production recommendation semantics at each point in time.
    """
    cutoff_at = _as_cutoff(cutoff)
    events: list[tuple[str, tuple[int, ...], int]] = []
    ordered = visits.sort_values(["pilot", "visit_at", "site_id"], kind="mergesort")
    for pilot, group in ordered.groupby("pilot", sort=True):
        sites = group["site_id"].astype(int).tolist()
        visit_times = group["visit_at"].tolist()
        for index in range(min_history, len(sites)):
            if pd.Timestamp(visit_times[index]) < cutoff_at:
                continue
            events.append((str(pilot), tuple(sites[:index]), sites[index]))
    return events


def events_fingerprint(
    events: list[tuple[str, tuple[int, ...], int]],
) -> str:
    """Fingerprint the exact ordered benchmark examples used for evaluation."""
    hasher = hashlib.sha256()
    for pilot, source_ids, target_id in events:
        payload = [pilot, list(source_ids), int(target_id)]
        hasher.update(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        )
        hasher.update(b"\n")
    return f"sha256:{hasher.hexdigest()}"


def dataset_fingerprint(visits: pd.DataFrame) -> str:
    canonical = visits.sort_values(
        ["pilot", "visit_at", "site_id"], kind="mergesort"
    ).reset_index(drop=True)
    hashed = pd.util.hash_pandas_object(canonical, index=False).values
    digest = hashlib.sha256(hashed.tobytes()).hexdigest()
    return f"sha256:{digest}"
