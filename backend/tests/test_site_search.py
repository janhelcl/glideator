from types import SimpleNamespace

import pytest

from app.services import site_search
from app.services.site_search import normalize_site_search_text, rank_site_matches


def _site(site_id: int, name: str):
    return SimpleNamespace(site_id=site_id, name=name)


def test_normalization_is_case_accent_and_whitespace_insensitive():
    assert normalize_site_search_text("  KÖSSEN  ") == "kossen"
    assert normalize_site_search_text("Raná") == normalize_site_search_text("rana")
    assert normalize_site_search_text("Monte   Grappa") == "monte grappa"


def test_ranking_prefers_exact_then_prefix_then_substring():
    sites = [
        _site(1, "Dolní Raná"),
        _site(2, "Raná hora"),
        _site(3, "Raná"),
    ]

    results = rank_site_matches(sites, "rana")

    assert [result.site_id for result in results] == [3, 2, 1]


def test_typo_tolerant_search_finds_close_site_name():
    sites = [
        _site(1, "Bassano"),
        _site(2, "Meduno"),
        _site(3, "Kössen"),
    ]

    results = rank_site_matches(sites, "Basano")

    assert [result.name for result in results] == ["Bassano"]


def test_typo_tolerance_works_for_partial_multiword_site_names():
    sites = [
        _site(1, "Monte Grappa Bassano"),
        _site(2, "Monte Baldo"),
    ]

    results = rank_site_matches(sites, "Basano")

    assert [result.name for result in results] == ["Monte Grappa Bassano"]


def test_short_queries_do_not_enable_fuzzy_matching():
    sites = [_site(1, "Raná"), _site(2, "Rasa")]

    results = rank_site_matches(sites, "rao")

    assert results == []


def test_limit_is_applied_after_ranking():
    sites = [_site(1, "Raná"), _site(2, "Raná hora"), _site(3, "Dolní Raná")]

    results = rank_site_matches(sites, "rana", limit=2)

    assert [result.site_id for result in results] == [1, 2]


@pytest.mark.parametrize("query", ["", "   "])
def test_empty_query_is_rejected(query):
    with pytest.raises(ValueError, match="query must not be empty"):
        rank_site_matches([], query)


@pytest.mark.parametrize("limit", [0, 51])
def test_invalid_limit_is_rejected(limit):
    with pytest.raises(ValueError, match="limit must be between 1 and 50"):
        rank_site_matches([], "rana", limit=limit)



def test_exact_alias_beats_canonical_prefix_match():
    sites = [
        _site(1, "Bassano"),
        _site(2, "Monte Grappa Ridge"),
    ]
    aliases = {1: ["Monte Grappa"]}

    results = rank_site_matches(
        sites,
        "Monte Grappa",
        aliases_by_site=aliases,
    )

    assert [result.site_id for result in results] == [1, 2]
    assert results[0].name == "Bassano"


def test_exact_canonical_name_beats_exact_alias_match():
    sites = [
        _site(1, "Bassano"),
        _site(2, "Monte Grappa"),
    ]
    aliases = {1: ["Monte Grappa"]}

    results = rank_site_matches(
        sites,
        "Monte Grappa",
        aliases_by_site=aliases,
    )

    assert [result.site_id for result in results] == [2, 1]


def test_alias_search_returns_each_site_only_once():
    sites = [_site(1, "Bassano")]
    aliases = {1: ["Monte Grappa", "Grappa"]}

    results = rank_site_matches(
        sites,
        "Grappa",
        aliases_by_site=aliases,
    )

    assert [(result.site_id, result.name) for result in results] == [(1, "Bassano")]


def test_fuzzy_matching_works_through_aliases():
    sites = [
        _site(1, "Meduno"),
        _site(2, "Bassano"),
    ]
    aliases = {
        1: ["Valinis"],
        2: ["Monte Grappa"],
    }

    results = rank_site_matches(
        sites,
        "Valins",
        aliases_by_site=aliases,
    )

    assert [(result.site_id, result.name) for result in results] == [(1, "Meduno")]



@pytest.mark.asyncio
async def test_search_sites_loads_aliases_from_database(monkeypatch):
    async def fake_get_site_list(db):
        return [_site(133, "Bassano"), _site(135, "Meduno")]

    class AliasResult:
        def all(self):
            return [
                (133, "Monte Grappa"),
                (135, "Monte Valinis"),
            ]

    class FakeDb:
        async def execute(self, statement):
            return AliasResult()

    monkeypatch.setattr(site_search.crud, "get_site_list", fake_get_site_list)

    results = await site_search.search_sites(
        FakeDb(),
        query="Monte Grappa",
    )

    assert [(result.site_id, result.name) for result in results] == [(133, "Bassano")]
