"""Shared site-search ranking used by REST and MCP surfaces.

Keep this module independent of transport-specific schemas so search semantics stay
consistent without coupling the public MCP contract to web-only changes.
"""

from collections import defaultdict
from difflib import SequenceMatcher
from typing import Iterable, List, Mapping
import unicodedata

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, models, schemas


_MIN_FUZZY_QUERY_LENGTH = 4
_MIN_FUZZY_RATIO = 0.72


def normalize_site_search_text(value: str) -> str:
    """Normalize whitespace, case and accents for deterministic site matching."""
    normalized = unicodedata.normalize("NFKD", value.strip().casefold())
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return " ".join(without_accents.split())


def _fuzzy_ratio(cleaned_query: str, cleaned_name: str) -> float:
    """Compare against both the full name and similarly sized word windows.

    Word-window matching keeps typo tolerance useful for partial names such as
    "Basano" -> "Monte Grappa Bassano" without making ordinary substring ranking fuzzy.
    """
    query_word_count = len(cleaned_query.split())
    name_words = cleaned_name.split()
    candidates = [cleaned_name]

    if query_word_count <= len(name_words):
        candidates.extend(
            " ".join(name_words[index:index + query_word_count])
            for index in range(len(name_words) - query_word_count + 1)
        )

    return max(SequenceMatcher(None, cleaned_query, candidate).ratio() for candidate in candidates)


def _match_rank(name: str, cleaned_query: str, source_priority: int = 0):
    """Return a sortable rank tuple, or None when the candidate should not match.

    source_priority keeps canonical names ahead of aliases within the same match
    class while still allowing an exact alias to beat a canonical prefix match.
    """
    cleaned_name = normalize_site_search_text(name)

    if cleaned_name == cleaned_query:
        return (0, source_priority, 0.0, len(cleaned_name), cleaned_name)
    if cleaned_name.startswith(cleaned_query):
        return (1, source_priority, 0.0, len(cleaned_name), cleaned_name)
    if cleaned_query in cleaned_name:
        return (2, source_priority, 0.0, len(cleaned_name), cleaned_name)

    if len(cleaned_query) < _MIN_FUZZY_QUERY_LENGTH:
        return None

    ratio = _fuzzy_ratio(cleaned_query, cleaned_name)
    if ratio < _MIN_FUZZY_RATIO:
        return None

    # Higher similarity should sort first, hence the negative value.
    return (3, source_priority, -ratio, len(cleaned_name), cleaned_name)


def rank_site_matches(
    sites: Iterable[object],
    query: str,
    limit: int = 10,
    aliases_by_site: Mapping[int, Iterable[str]] | None = None,
) -> List[schemas.SiteListItem]:
    """Rank sites using canonical names and aliases without duplicating results.

    Ranking order is exact, prefix, substring, then conservative fuzzy match.
    Within each class a canonical-name match wins over an alias match.
    """
    cleaned_query = normalize_site_search_text(query)
    if not cleaned_query:
        raise ValueError("query must not be empty")
    if limit < 1 or limit > 50:
        raise ValueError("limit must be between 1 and 50")

    aliases_by_site = aliases_by_site or {}
    ranked = []

    for row in sites:
        candidate_ranks = []

        canonical_rank = _match_rank(row.name, cleaned_query, source_priority=0)
        if canonical_rank is not None:
            candidate_ranks.append(canonical_rank)

        for alias in aliases_by_site.get(row.site_id, ()):
            alias_rank = _match_rank(alias, cleaned_query, source_priority=1)
            if alias_rank is not None:
                candidate_ranks.append(alias_rank)

        if not candidate_ranks:
            continue

        best_rank = min(candidate_ranks)
        deterministic_rank = best_rank + (
            normalize_site_search_text(row.name),
            row.site_id,
        )
        ranked.append((deterministic_rank, row))

    ranked.sort(key=lambda item: item[0])
    return [
        schemas.SiteListItem(site_id=row.site_id, name=row.name)
        for _, row in ranked[:limit]
    ]


async def search_sites(
    db: AsyncSession,
    query: str,
    limit: int = 10,
) -> List[schemas.SiteListItem]:
    """Search the current site directory with shared deterministic semantics."""
    sites = await crud.get_site_list(db)

    alias_result = await db.execute(
        select(models.SiteAlias.site_id, models.SiteAlias.alias)
    )
    aliases_by_site = defaultdict(list)
    for site_id, alias in alias_result.all():
        aliases_by_site[site_id].append(alias)

    return rank_site_matches(
        sites,
        query=query,
        limit=limit,
        aliases_by_site=aliases_by_site,
    )
