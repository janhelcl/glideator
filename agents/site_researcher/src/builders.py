from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Sequence

import pandas as pd
from string import Template


def _load_site_id_to_text_map(jsonl_path: str) -> Dict[int, str]:
    site_id_to_text: Dict[int, str] = {}
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            site_id = obj.get("site_id")
            text = obj.get("text")
            if isinstance(site_id, int) and isinstance(text, str) and text.strip():
                site_id_to_text[site_id] = text
    return site_id_to_text


def make_build_tag_extractor_requests(
    sites_df: pd.DataFrame,
    overview_jsonl_path: str,
    access_jsonl_path: str,
    risk_jsonl_path: str,
    prompt_template: Template,
) -> Callable[[Sequence[int]], List[dict]]:
    """Create a request builder for the tag_extractor template.

    The builder reads three per-site report files (overview, access, risk),
    concatenates their texts, and injects them into the provided template.
    The returned function conforms to the `build_requests_fn` signature
    required by `run_iterative_batch`.
    """
    overview_map = _load_site_id_to_text_map(overview_jsonl_path)
    access_map = _load_site_id_to_text_map(access_jsonl_path)
    risk_map = _load_site_id_to_text_map(risk_jsonl_path)

    def build_requests(site_ids: Sequence[int]) -> List[dict]:
        subset = sites_df[sites_df["site_id"].isin(site_ids)].copy()
        subset = subset.sort_values("site_id")
        requests: List[dict] = []
        for _, row in subset.iterrows():
            site_id = int(row["site_id"])  # type: ignore[arg-type]
            site_name = row["name"]

            report_segments: List[str] = []
            overview_text = overview_map.get(site_id)
            if overview_text:
                report_segments.append("Overview:\n" + overview_text)
            access_text = access_map.get(site_id)
            if access_text:
                report_segments.append("Access:\n" + access_text)
            risk_text = risk_map.get(site_id)
            if risk_text:
                report_segments.append("Risks:\n" + risk_text)

            reports = "\n\n".join(report_segments).strip()
            prompt_text = prompt_template.safe_substitute(site_name=site_name, reports=reports)

            requests.append({
                "key": site_id,
                "request": {
                    "contents": [{
                        "parts": [{"text": prompt_text}],
                        "role": "user",
                    }],
                    "generation_config": {"temperature": 0},
                },
            })
        return requests

    return build_requests


def build_requests_for_site_ids(site_ids: list[int], sites_df: pd.DataFrame, prompt_template: Template) -> list[dict]:
    subset = sites_df[sites_df["site_id"].isin(site_ids)].copy()
    subset = subset.sort_values("site_id")
    return [
        {
            "key": int(row["site_id"]),
            "request": {
                "contents": [{
                    "parts": [{
                        "text": prompt_template.safe_substitute(site_name=row["name"], country=row["country"]) 
                    }],
                    "role": "user",
                }],
                "tools": [{"google_search": {}}],
                "generation_config": {"temperature": 0}
            }
        }
        for _, row in subset.iterrows()
    ]