"""Shared site-search ranking used by REST and MCP surfaces.

Keep this module independent of transport-specific schemas so search semantics stay
consistent without coupling the public MCP contract to web-only changes.
"""

from difflib import SequenceMatcher
import unicodedata
from typing import Iterable, List

from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas


_MIN_FUZZY_QUERY_LENGTH = 4
_MIN_FUZZY_RATIO = 0.72


def normalize_site_search_text(value: str) -> str:
    """Normalize whitespace, case and accents for deterministic site matching."""
    normalized = unicodedata.normalize("NFKD", value.strip().casefold())
    without_accents = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return " ".join(without_accents.split())


def _match_rank(name: str, cleaned_query: str):
    """Return a sortable rank tuple, or None when the candidate should not match."""
    cleaned_name = normalize_site_search_text(name)

    if cleaned_name == cleaned_query:
        return (0, 0.0, len(cleaned_name), cleaned_name)
    if cleaned_name.startswith(cleaned_query):
        return (1, 0.0, len(cleaned_name), cleaned_name)
    if cleaned_query in cleaned_name:
        return (2, 0.0, len(cleaned_name), cleaned_name)

    if len(cleaned_query) < _MIN_FUZZY_QUERY_LENGTH:
        return None

    ratio = SequenceMatcher(None, cleaned_query, cleaned_name).ratio()
    if ratio < _MIN_FUZZY_RATIO:
        return None

    # Higher similarity should sort first, hence the negative value.
    return (3, -ratio, len(cleaned_name), cleaned_name)


def rank_site_matches(
    sites: Iterable[object],
    query: str,
    limit: int = 10,
) -> List[schemas.SiteListItem]:
    """Rank site rows by exact, prefix, substring, then conservative fuzzy match."""
    cleaned_query = normalize_site_search_text(query)
    if not cleaned_query:
        raise ValueError("query must not be empty")
    if limit < 1 or limit > 50:
        raise ValueError("limit must be between 1 and 50")

    ranked = []
    for row in sites:
        rank = _match_rank(row.name, cleaned_query)
        if rank is None:
            continue
        ranked.append((rank, row))

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
    return rank_site_matches(sites, query=query, limit=limit)
