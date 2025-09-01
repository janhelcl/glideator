from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Sequence, Tuple

try:
    # Prefer runtime imports; callers will ensure the SDK is installed/available
    from google.genai import Client
    from google.genai import types
except Exception:  # pragma: no cover - allows type checking without SDK at import-time
    Client = Any  # type: ignore
    types = Any  # type: ignore


# Module logger
logger = logging.getLogger(__name__)


# Type aliases for clarity
BuildRequestsFn = Callable[[Sequence[Any]], List[dict]]
ParseResultFn = Callable[[dict], Tuple[Any, Any] | None]


def submit_batch_and_download_raw(
    client: Client,
    requests: List[dict],
    job_name: str,
    poll_interval_sec: int = 30,
    *,
    model: str = "gemini-2.5-pro",
    batch_config: Dict[str, Any] | None = None,
    upload_mime_type: str = "jsonl",
) -> List[dict]:
    """Submit a JSONL batch and return raw JSONL results as a list of dicts.

    This function expects each request to be a dict with keys:
      - "key": a unique identifier for the request (e.g., site_id)
      - "request": the provider-specific request payload

    The file is uploaded, the batch is created, then polled until completion.
    The result file is downloaded and split into JSON objects.
    """
    # Ensure batch_requests directory exists
    batch_requests_dir = Path("batch_requests")
    batch_requests_dir.mkdir(exist_ok=True)
    
    tmp_file = batch_requests_dir / f"{job_name}_input.jsonl"
    logger.info("Submitting batch '%s' with %d requests", job_name, len(requests))
    with open(tmp_file, "w", encoding="utf-8") as f:
        for req in requests:
            f.write(json.dumps(req, ensure_ascii=False) + "\n")
    logger.debug("Wrote JSONL input to %s", tmp_file)

    uploaded_file = client.files.upload(
        file=tmp_file,
        config=types.UploadFileConfig(display_name=str(tmp_file), mime_type=upload_mime_type)
    )
    logger.debug("Uploaded file id: %s", getattr(uploaded_file, "name", "<unknown>"))

    effective_config = {'display_name': job_name}
    if batch_config:
        effective_config.update(batch_config)
    batch_job = client.batches.create(
        model=model,
        src=uploaded_file.name,
        config=effective_config,
    )
    logger.info("Created batch job '%s' (model=%s)", getattr(batch_job, "name", job_name), model)

    completed_states = {
        'JOB_STATE_SUCCEEDED',
        'JOB_STATE_FAILED',
        'JOB_STATE_CANCELLED',
        'JOB_STATE_EXPIRED',
        # Some SDKs may expose transient enum names like BATCH_STATE_*; we guard in the loop
    }

    name = batch_job.name
    start_ts = time.time()
    while True:
        bj = client.batches.get(name=name)
        state = bj.state.name
        elapsed = int(time.time() - start_ts)
        logger.info("Batch '%s' state=%s elapsed=%ss", name, state, elapsed)
        if state in completed_states or state == 'BATCH_STATE_SUCCEEDED':
            break
        time.sleep(poll_interval_sec)

    if bj.state.name == 'JOB_STATE_FAILED':
        logger.error("Batch '%s' failed: %s", name, getattr(bj, "error", "<no error message>"))
        # Return an empty list so callers can decide on retry behavior
        return []

    content = client.files.download(file=bj.dest.file_name)
    raw_lines: List[dict] = []
    # content is a bytes or str containing JSON Lines
    if isinstance(content, (bytes, bytearray)):
        content = content.decode("utf-8", errors="ignore")
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw_lines.append(json.loads(line))
        except Exception:
            # Skip malformed lines rather than failing the whole batch
            pass
    logger.info("Downloaded %d result lines for batch '%s'", len(raw_lines), name)
    return raw_lines


def run_iterative_batch(
    client: Client,
    items: Sequence[Any],
    build_requests_fn: BuildRequestsFn,
    parse_result_fn: ParseResultFn,
    job_name_prefix: str,
    max_retries: int = 3,
    poll_interval_sec: int = 30,
    *,
    model: str = "gemini-2.5-pro",
    batch_config: Dict[str, Any] | None = None,
    upload_mime_type: str = "jsonl",
) -> Tuple[Dict[Any, Any], List[Any]]:
    """Run a batch job iteratively, retrying failures until success or max_retries.

    Parameters:
      - client: provider SDK client
      - items: sequence of items to process (e.g., site_ids)
      - build_requests_fn: function that builds a list of request lines for a subset of items
      - parse_result_fn: function that takes a raw result line and returns (key, value) or None if failed
      - job_name_prefix: prefix for created batch job names/files
      - max_retries: number of attempts (1 initial + retries)
      - poll_interval_sec: polling interval when waiting for job completion

    Returns:
      - mapping from item key to parsed value
      - list of items that remained unresolved after retries
    """
    remaining: List[Any] = list(items)
    resolved: Dict[Any, Any] = {}

    for attempt in range(1, max_retries + 1):
        if not remaining:
            break

        job_name = f"{job_name_prefix}_attempt_{attempt}-{int(time.time())}"
        logger.info("Attempt %d: processing %d items", attempt, len(remaining))
        requests = build_requests_fn(remaining)
        raw = submit_batch_and_download_raw(
            client,
            requests,
            job_name=job_name,
            poll_interval_sec=poll_interval_sec,
            model=model,
            batch_config=batch_config,
            upload_mime_type=upload_mime_type,
        )

        # Parse raw lines into successes/failures
        seen_keys: set[Any] = set()
        next_remaining: List[Any] = []
        parsed_successes = 0
        for r in raw:
            try:
                parsed = parse_result_fn(r)
            except Exception:
                parsed = None
            if parsed is None:
                # Failed parse; if the raw result carries a key, carry it over; else it will be retried as unknown
                k = r.get("key") if isinstance(r, dict) else None
                if k is not None and k in remaining:
                    next_remaining.append(k)
                continue
            k, v = parsed
            seen_keys.add(k)
            resolved[k] = v
            parsed_successes += 1

        # Any items not seen in results stay in the remaining set
        for k in remaining:
            if k not in seen_keys and k not in resolved:
                next_remaining.append(k)

        remaining = list(dict.fromkeys(next_remaining))  # stable, deduplicated
        logger.info(
            "Attempt %d complete: successes=%d, unresolved_now=%d",
            attempt,
            parsed_successes,
            len(remaining),
        )

    return resolved, remaining


# Default parser for Google Generative AI JSONL batch responses
def parse_result_google_text(result: dict) -> Tuple[Any, str] | None:
    """Extract (key, text) from a Google batch result line.

    Returns None if the expected text is missing.
    """
    try:
        key = result.get("key")
        cands = result["response"]["candidates"]
        if not cands:
            return None
        content = cands[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            return None
        text = parts[0].get("text")
        if not isinstance(text, str) or not text.strip():
            return None
        return key, text
    except Exception:
        return None


