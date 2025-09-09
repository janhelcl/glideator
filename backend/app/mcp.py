from typing import List, Dict, Optional
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from pydantic import TypeAdapter
from app import crud
from app.database import AsyncSessionLocal
from app import schemas


mcp = FastMCP("Glideator-MCP")


@mcp.tool()
async def list_sites() -> List[schemas.SiteListItem]:
    """Get list of all available sites with their IDs and names"""
    async with AsyncSessionLocal() as db:
        sites_raw = await crud.get_site_list(db)
    
    # Use TypeAdapter to convert SQLAlchemy Row objects to Pydantic schemas
    adapter = TypeAdapter(List[schemas.SiteListItem])
    sites_data = [{"site_id": row.site_id, "name": row.name} for row in sites_raw]
    sites = adapter.validate_python(sites_data)
    return sites


@mcp.tool()
async def get_site_info(site_id: int) -> schemas.SiteInfo:
    """Get site info by ID
    
    Returns an HTML string with comprehensive information about the site.
    Usually includes description, facilities, access, risks, limitations, etc.
    """
    async with AsyncSessionLocal() as db:
        site_info_model = await crud.get_site_info(db, site_id)
    
    if site_info_model is None:
        return None
    # Convert SQLAlchemy model to Pydantic schema
    site_info = schemas.SiteInfo(
        site_id=site_info_model.site_id,
        site_name=site_info_model.site_name,
        country=site_info_model.country,
        html=site_info_model.html
    )
    return site_info


@mcp.tool()
async def get_site_seasonal_stats(site_id: int) -> Dict[str, Dict[str, float]]:
    """Return historical seasonality for a site as average counts of flyable days per month.
    
    - Keys (level 1): month names ("January" ... "December").
    - Values (level 2): mapping of XC thresholds to the average number of days in that month
      (across historical years) with at least that XC score.
    - XC metric meaning in this context (counts, not probabilities):
      - 'days_over_0XC_points_or_more': average days with any flight (>= 0 XC points)
      - 'days_over_10XC_points_or_more': average days with flights worth >= 10 XC points
      - ... up to 'days_over_100XC_points_or_more'
    """
    async with AsyncSessionLocal() as db:
        site_seasonal_stats = await crud.get_flight_stats_by_site_id(db, site_id)
    
    # Month mapping
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August", 
        9: "September", 10: "October", 11: "November", 12: "December"
    }
    
    # Build the result dictionary
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


@mcp.tool()
async def get_site_predictions(site_id: int, query_date: Optional[str] = None) -> Dict[str, Dict[str, float]]:
    """Return forecast probabilities for a site's flyability, optionally filtered by date.
    
    - Input: site_id; optional query_date as 'YYYY-MM-DD'.
    - Keys (level 1): ISO dates ('YYYY-MM-DD').
    - Values (level 2): mapping of XC thresholds to probabilities in [0, 1].
    - XC metric meaning in this context (probabilities for that specific date):
      - 'probability_of_flight_over_0XC_points_or_more': probability of any flyable flight (>= 0 XC points)
      - 'probability_of_flight_over_10XC_points_or_more': probability of a flight worth >= 10 XC points
      - ... up to 'probability_of_flight_over_100XC_points_or_more'
    """
    async with AsyncSessionLocal() as db:
        # Convert string date to date object if provided
        date_filter = None
        if query_date:
            try:
                date_filter = datetime.strptime(query_date, "%Y-%m-%d").date()
            except ValueError:
                raise ValueError("Date must be in YYYY-MM-DD format")
        
        predictions = await crud.get_predictions(db, site_id, query_date=date_filter)
    
    if not predictions:
        return {}
    
    # Group predictions by date
    result = {}
    for pred in predictions:
        date_str = pred.date.strftime("%Y-%m-%d")
        if date_str not in result:
            result[date_str] = {}
        
        # Transform metric name to more descriptive key
        # Extract the number from metric like "XC0", "XC10", etc.
        if pred.metric.startswith("XC"):
            points = pred.metric[2:]  # Remove "XC" prefix
            descriptive_key = f"probability_of_flight_over_{points}XC_points_or_more"
        else:
            # Fallback for any non-XC metrics
            descriptive_key = pred.metric
            
        result[date_str][descriptive_key] = pred.value
    
    return result
