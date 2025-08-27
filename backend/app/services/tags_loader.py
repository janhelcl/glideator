import json
import os
import logging
from typing import List, Any

from sqlalchemy.orm import Session

from .. import crud

logger = logging.getLogger(__name__)

def _parse_tags_field(raw: Any) -> List[str]:
    if raw is None:
        return []
    # If already a list
    if isinstance(raw, list):
        result: List[str] = []
        for item in raw:
            if isinstance(item, str) and item.strip():
                result.append(item.strip())
            elif isinstance(item, dict):
                val = item.get('tag') or item.get('name') or item.get('value')
                if isinstance(val, str) and val.strip():
                    result.append(val.strip())
        return result
    # If string: could be JSON, delimited text, or code-fenced JSON
    if isinstance(raw, str):
        text = raw.strip()
        if text.startswith('```') and text.endswith('```'):
            inner = text[3:-3]
            inner = inner.lstrip()
            if inner.startswith('json'):
                inner = inner[4:]
            inner = inner.strip()
            try:
                parsed = json.loads(inner)
                return _parse_tags_field(parsed)
            except Exception:
                # Fallback: split lines (ignore brackets)
                lines = []
                for ln in inner.splitlines():
                    val = ln.strip().strip(',').strip('[').strip(']').strip('"')
                    if val:
                        lines.append(val)
                return [t for t in (v.strip() for v in lines) if t]
        # Try JSON array first
        try:
            parsed = json.loads(text)
            return _parse_tags_field(parsed)
        except Exception:
            # Fallback: comma/semicolon delimited
            return [t.strip() for t in text.replace(';', ',').split(',') if t.strip()]
    # Unknown shape
    return []

def load_tags_from_jsonl(db: Session, filename: str = 'tags.jsonl'):
    jsonl_path = os.path.join(os.path.dirname(__file__), '..', 'data', filename)
    logger.info(f"Loading site tags from {jsonl_path}")

    if not os.path.exists(jsonl_path):
        logger.warning(f"Tags file not found at {jsonl_path}; skipping tags load")
        return

    loaded = 0
    non_empty = 0
    with open(jsonl_path, mode='r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)

            site_id_value: Any = data.get('site_id') or data.get('id') or data.get('siteId')
            if site_id_value is None:
                logger.warning(f"Skipping line without site_id: {data}")
                continue
            try:
                site_id = int(site_id_value)
            except Exception:
                logger.warning(f"Skipping line with non-integer site_id: {data}")
                continue

            raw_tags = data.get('tags')
            if raw_tags is None:
                # common alternate field from batch results
                raw_tags = data.get('text')
            tags = _parse_tags_field(raw_tags)

            crud.replace_site_tags(db, site_id, tags)
            loaded += 1
            if tags:
                non_empty += 1

    logger.info(f"Tag load complete: {loaded} sites processed, {non_empty} with non-empty tags")

