import unicodedata
from datetime import datetime
from typing import Dict, List, Literal, Optional

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field, TypeAdapter

from app import crud, schemas
from app.database import AsyncSessionLocal
from app.services import site_search, trip_planner_service


READ_ONLY_ANNOTATIONS = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    openWorldHint=False,
)


class PublicSiteResources(BaseModel):
    """Public MCP shape for curated site resources without extraction-run metadata."""

    site_id: int
    local_resources: List[schemas.SiteResourceLink] = Field(default_factory=list)
    webcam_url: Optional[str] = None
    webcam_urls: List[str] = Field(default_factory=list)
    meteostation_url: Optional[str] = None
    meteostation_urls: List[str] = Field(default_factory=list)


def _normalize_site_name(value: str) -> str:
    """Normalize case and accents so e.g. 'Rana' matches 'Raná'."""
    normalized = unicodedata.normalize("NFKD", value.strip().casefold())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _serialize_site_info(value: object) -> schemas.SiteInfo:
    """Convert the ORM site-info record to the public Pydantic response shape."""
    return schemas.SiteInfo.model_validate(value)


mcp = FastMCP(
    "Parra-Glideator",
    instructions=(
        "Read-only paragliding planning data from Parra-Glideator. Use these tools to compare "
        "forecast-derived flight and XC potential, site descriptions, historical seasonality, "
        "launch/landing data, and curated local resources. The results are decision support, not "
        "a determination that conditions are safe or legal to fly. Users must verify current "
        "weather, local rules, airspace, site access, and suitability for their skills and "
        "equipment before flying."
    ),
    # Remote MCP clients should not depend on an in-memory session surviving
    # proxies, reconnects, or deploys. JSON responses also avoid an SSE stream
    # for ordinary read-only tool calls.
    stateless_http=True,
    json_response=True,
)


@mcp.tool(title="Find paragliding sites", annotations=READ_ONLY_ANNOTATIONS)
async def find_sites(query: str, limit: int = 10) -> List[schemas.SiteListItem]:
    """Use this when the user names or searches for a paragliding site and you need its site ID.

    Performs a case-insensitive, accent-insensitive name match against Parra-Glideator's site
    directory. Prefer this over list_sites when the user already supplied a site or place name.

    Args:
        query: Full or partial site name, for example "Bassano", "Rana", or "Annecy".
        limit: Maximum matches to return. Must be between 1 and 50.
    """
    async with AsyncSessionLocal() as db:
        return await site_search.search_sites(db, query=query, limit=limit)


@mcp.tool(title="List paragliding sites", annotations=READ_ONLY_ANNOTATIONS)
async def list_sites() -> List[schemas.SiteListItem]:
    """Use this when the user wants to browse all paragliding sites covered by Parra-Glideator.

    Returns the complete site directory with stable site IDs and names. If the user already named
    a specific site, prefer find_sites to avoid returning the full directory.
    """
    async with AsyncSessionLocal() as db:
        sites_raw = await crud.get_site_list(db)

    adapter = TypeAdapter(List[schemas.SiteListItem])
    sites_data = [{"site_id": row.site_id, "name": row.name} for row in sites_raw]
    return adapter.validate_python(sites_data)


@mcp.tool(title="Get site overview", annotations=READ_ONLY_ANNOTATIONS)
async def get_site_info(site_id: int) -> schemas.SiteInfo:
    """Use this when the user asks for a general overview or description of a known site.

    Returns Parra-Glideator's stored site guide, including descriptive information such as local
    characteristics, access, facilities, and rules where available. This is editorial/reference
    information, not a live safety assessment; verify current local rules and conditions before use.

    Args:
        site_id: Parra-Glideator site ID. Use find_sites when the ID is unknown.
    """
    async with AsyncSessionLocal() as db:
        site_info = await crud.get_site_info(db, site_id)

    if not site_info:
        raise ValueError(f"No stored site overview found for site {site_id}")
    return _serialize_site_info(site_info)


@mcp.tool(title="Get site resources", annotations=READ_ONLY_ANNOTATIONS)
async def get_site_resources(site_id: int) -> PublicSiteResources:
    """Use this when the user wants practical local links for a known paragliding site.

    Returns curated club/site pages, webcams, and meteostation links already stored by
    Parra-Glideator as structured data. This tool does not browse those external sites or change
    external state.

    Args:
        site_id: Parra-Glideator site ID. Use find_sites when the ID is unknown.
    """
    async with AsyncSessionLocal() as db:
        resources = await crud.get_site_resources(db, site_id)

    public_data = resources.model_dump(exclude={"source_run_id", "run_extracted_at"})
    return PublicSiteResources.model_validate(public_data)


@mcp.tool(title="Get site seasonal statistics", annotations=READ_ONLY_ANNOTATIONS)
async def get_site_seasonal_stats(site_id: int) -> Dict[str, Dict[str, float]]:
    """Use this when the user asks when a paragliding site historically performs best.

    Returns average days per month reaching XC activity thresholds from 0 through 100 points.
    These are historical flight-activity statistics, not a safety assessment or future forecast.

    Args:
        site_id: Parra-Glideator site ID. Use find_sites when the ID is unknown.
    """
    async with AsyncSessionLocal() as db:
        site_seasonal_stats = await crud.get_flight_stats_by_site_id(db, site_id)

    month_names = {
        1: "January",
        2: "February",
        3: "March",
        4: "April",
        5: "May",
        6: "June",
        7: "July",
        8: "August",
        9: "September",
        10: "October",
        11: "November",
        12: "December",
    }

    result = {}
    for stats in site_seasonal_stats:
        month_name = month_names[stats.month]
        result[month_name] = {
            "days_over_0XC_points_or_more": stats.avg_days_over_0,
            "days_over_10XC_points_or_more": stats.avg_days_over_10,
            "days_over_20XC_points_or_more": stats.avg_days_over_20,
            "days_over_30XC_points_or_more": stats.avg_days_over_30,
            "days_over_40XC_points_or_more": stats.avg_days_over_40,
            "days_over_50XC_points_or_more": stats.avg_days_over_50,
            "days_over_60XC_points_or_more": stats.avg_days_over_60,
            "days_over_70XC_points_or_more": stats.avg_days_over_70,
            "days_over_80XC_points_or_more": stats.avg_days_over_80,
            "days_over_90XC_points_or_more": stats.avg_days_over_90,
            "days_over_100XC_points_or_more": stats.avg_days_over_100,
        }

    return result


@mcp.tool(title="Get site flight-potential forecast", annotations=READ_ONLY_ANNOTATIONS)
async def get_site_predictions(
    site_id: int,
    query_date: Optional[str] = None,
) -> Dict[str, Dict[str, float]]:
    """Use this when the user asks about forecast-derived paragliding potential at one site.

    Returns modelled probabilities for XC activity thresholds from 0 through 100 points. Forecasts
    are typically available for the next seven days. A high probability means the forecast looks
    similar to weather associated with that level of past flight activity; it does not mean the
    site is safe, legal, or suitable for a particular pilot.

    Args:
        site_id: Parra-Glideator site ID. Use find_sites when the ID is unknown.
        query_date: Optional date in YYYY-MM-DD format. Omit to return all available forecast dates.
    """
    async with AsyncSessionLocal() as db:
        date_filter = None
        if query_date:
            try:
                date_filter = datetime.strptime(query_date, "%Y-%m-%d").date()
            except ValueError as exc:
                raise ValueError("query_date must be in YYYY-MM-DD format") from exc

        predictions = await crud.get_predictions(db, site_id, query_date=date_filter)

    if not predictions:
        return {}

    result = {}
    ordered_predictions = sorted(
        predictions,
        key=lambda pred: (
            pred.date,
            int(pred.metric[2:])
            if pred.metric.startswith("XC") and pred.metric[2:].isdigit()
            else 10_000,
            pred.metric,
        ),
    )
    for pred in ordered_predictions:
        date_str = pred.date.strftime("%Y-%m-%d")
        if date_str not in result:
            result[date_str] = {}

        if pred.metric.startswith("XC"):
            points = pred.metric[2:]
            descriptive_key = f"probability_of_flight_over_{points}XC_points_or_more"
        else:
            descriptive_key = pred.metric

        result[date_str][descriptive_key] = pred.value

    return result


@mcp.tool(title="Get site takeoffs and landings", annotations=READ_ONLY_ANNOTATIONS)
async def get_site_takeoffs_and_landings(site_id: int) -> List[schemas.Spot]:
    """Use this when the user asks where launches or landings are at a known paragliding site.

    Returns stored coordinates, elevation, spot type, and suitable wind-direction metadata where
    available. Treat this as orientation data only; users must verify current site rules, access,
    obstacles, and local conditions before use.

    Args:
        site_id: Parra-Glideator site ID. Use find_sites when the ID is unknown.
    """
    async with AsyncSessionLocal() as db:
        spots_models = await crud.get_spots_by_site_id(db, site_id)

    adapter = TypeAdapter(List[schemas.Spot])
    return adapter.validate_python(spots_models)


@mcp.tool(title="Plan a paragliding trip", annotations=READ_ONLY_ANNOTATIONS)
async def plan_trip(
    start_date: str,
    end_date: str,
    metric: Literal[
        "XC0",
        "XC10",
        "XC20",
        "XC30",
        "XC40",
        "XC50",
        "XC60",
        "XC70",
        "XC80",
        "XC90",
        "XC100",
    ] = "XC0",
    user_latitude: Optional[float] = None,
    user_longitude: Optional[float] = None,
    max_distance_km: Optional[float] = None,
    min_altitude_m: Optional[int] = None,
    max_altitude_m: Optional[int] = None,
    required_tags: Optional[List[str]] = None,
    offset: int = 0,
    limit: int = 10,
) -> schemas.TripPlanResponse:
    """Use this when the user wants to compare or rank paragliding sites for specific dates.

    Combines forecast-derived flight/XC potential for near-term dates with historical fallback data
    and ranks matching sites. This is the primary tool for questions such as "Where should I look
    at flying this weekend?" or "Which sites have the strongest 50-point XC signal next week?"

    Do not present the ranking as a safety or go/no-go recommendation. The user must still verify
    current weather, airspace, local rules, access, and suitability for their skills and equipment.

    Args:
        start_date: Trip start date in YYYY-MM-DD format.
        end_date: Trip end date in YYYY-MM-DD format.
        metric: XC activity threshold to optimize, from XC0 through XC100 in 10-point steps.
        user_latitude: Optional origin latitude used for distance filtering/ranking.
        user_longitude: Optional origin longitude used for distance filtering/ranking.
        max_distance_km: Optional maximum straight-line distance from the supplied origin.
        min_altitude_m: Optional minimum site altitude in metres.
        max_altitude_m: Optional maximum site altitude in metres.
        required_tags: Optional site tags such as "car", "lift", "shuttle", "Alps", or "flats".
        offset: Number of ranked results to skip for pagination.
        limit: Maximum number of ranked sites to return.
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError("start_date and end_date must be in YYYY-MM-DD format") from exc

    if start > end:
        raise ValueError("start_date must be on or before end_date")
    if (user_latitude is None) != (user_longitude is None):
        raise ValueError("user_latitude and user_longitude must be supplied together")
    if user_latitude is not None and not -90 <= user_latitude <= 90:
        raise ValueError("user_latitude must be between -90 and 90")
    if user_longitude is not None and not -180 <= user_longitude <= 180:
        raise ValueError("user_longitude must be between -180 and 180")
    if max_distance_km is not None and max_distance_km <= 0:
        raise ValueError("max_distance_km must be greater than 0")
    if min_altitude_m is not None and max_altitude_m is not None and min_altitude_m > max_altitude_m:
        raise ValueError("min_altitude_m must be on or below max_altitude_m")
    if offset < 0:
        raise ValueError("offset must be 0 or greater")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")

    async with AsyncSessionLocal() as db:
        return await trip_planner_service.plan_trip_service(
            db=db,
            start_date=start,
            end_date=end,
            metric=metric,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            max_distance_km=max_distance_km,
            min_altitude_m=min_altitude_m,
            max_altitude_m=max_altitude_m,
            required_tags=required_tags,
            offset=offset,
            limit=limit,
        )
