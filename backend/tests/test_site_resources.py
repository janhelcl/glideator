"""Tests for ground-crew-backed site resources API."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app import crud


@pytest.fixture(autouse=True)
def _clear_site_resources_json_cache():
    crud.invalidate_site_resources_json_cache()
    yield
    crud.invalidate_site_resources_json_cache()


@pytest.mark.asyncio
async def test_get_site_resources_no_extraction_run():
    """When no extraction run exists, return empty payload."""
    db = AsyncMock()
    first_result = MagicMock()
    first_result.mappings.return_value.first.return_value = None
    db.execute = AsyncMock(return_value=first_result)

    out = await crud.get_site_resources(db, 42)

    assert out.site_id == 42
    assert out.source_run_id is None
    assert out.run_extracted_at is None
    assert out.local_resources == []
    assert out.webcam_urls == []
    assert out.meteostation_urls == []
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_site_resources_from_json_file(monkeypatch, tmp_path):
    """When SITE_RESOURCES_JSON_PATH is set, skip DB and use export JSON."""
    payload = [
        {
            "site_id": 99,
            "source_run_id": 1,
            "run_extracted_at": "2025-01-01T12:00:00",
            "local_resources": [
                {
                    "candidate_id": 10,
                    "name": "Example Club",
                    "url": "https://example.org/",
                    "host": "example.org",
                    "takeoff_landing_areas": True,
                    "rules": False,
                    "fees": None,
                    "access": True,
                    "meteostation": False,
                    "webcams": False,
                }
            ],
            "webcam_url": "https://example.org/cam",
            "webcam_urls": ["https://example.org/cam"],
            "meteostation_url": None,
            "meteostation_urls": [],
        }
    ]
    p = tmp_path / "site_resources.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("SITE_RESOURCES_JSON_PATH", str(p))

    db = AsyncMock()
    out = await crud.get_site_resources(db, 99)
    assert out.site_id == 99
    assert len(out.local_resources) == 1
    assert out.local_resources[0].url == "https://example.org/"
    assert out.webcam_url == "https://example.org/cam"
    db.execute.assert_not_awaited()

    missing = await crud.get_site_resources(db, 100)
    assert missing.local_resources == []
    db.execute.assert_not_awaited()
