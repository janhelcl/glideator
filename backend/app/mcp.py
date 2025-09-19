from typing import List, Dict, Optional
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from pydantic import TypeAdapter
from app import crud
from app.database import AsyncSessionLocal
from app import schemas
from app.services import trip_planner_service


mcp = FastMCP("Glideator-MCP")


@mcp.tool()
async def list_sites() -> List[schemas.SiteListItem]:
    """Get a complete list of all available paragliding sites with their IDs and names.
    
    This tool provides a directory of all paragliding sites in the database. Use this
    when users want to browse available sites, need to find a specific site by name,
    or want to get site IDs for use with other tools.
    
    Returns:
        List of sites with site_id and name. Use the site_id with other tools to get
        detailed information, forecasts, or statistics for specific sites.
    
    Use this when users ask about:
    - "What paragliding sites are available?"
    - "Show me all flying sites"
    - "List paragliding locations"
    - "What sites do you have data for?"
    """
    async with AsyncSessionLocal() as db:
        sites_raw = await crud.get_site_list(db)
    
    # Use TypeAdapter to convert SQLAlchemy Row objects to Pydantic schemas
    adapter = TypeAdapter(List[schemas.SiteListItem])
    sites_data = [{"site_id": row.site_id, "name": row.name} for row in sites_raw]
    sites = adapter.validate_python(sites_data)
    return sites


@mcp.tool()
async def get_site_info(site_id: int) -> schemas.SiteInfo:
    """Get detailed information about a specific paragliding site.
    
    This tool returns comprehensive site information including description, facilities,
    access instructions, safety information, risks, limitations, and local knowledge.
    The information is provided as HTML content that can be parsed and presented to users.
    
    Args:
        site_id: Unique identifier of the site (get from list_sites tool)
    
    Returns:
        Site information object containing site_id, site_name, country, and detailed
        HTML content with all available information about the site.
    
    Use this when users ask about:
    - "Tell me about [specific site name]"  
    - "What are the conditions at [site]?"
    - "How do I access [site name]?"
    - "What facilities are available at [site]?"
    - "Is [site] safe for beginners?"
    - "What are the risks at [site]?"
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
    """Get historical flying statistics showing seasonal patterns for a paragliding site.
    
    This tool provides historical data showing how many flyable days each month typically
    has at a specific site, broken down by different XC (cross-country) performance levels.
    Perfect for understanding the best months to visit a site or comparing seasonal patterns.
    
    Args:
        site_id: Unique identifier of the site (get from list_sites tool)
    
    Returns:
        Dictionary with month names as keys ("January" to "December"), each containing
        XC threshold statistics:
        - 'days_over_0XC_points_or_more': average days with any flyable conditions
        - 'days_over_10XC_points_or_more': average days suitable for 10+ XC point flights  
        - 'days_over_20XC_points_or_more': average days for 20+ XC point flights
        - ... up to 'days_over_100XC_points_or_more' for exceptional conditions
        
        Higher XC thresholds indicate better thermal/soaring conditions for longer flights.
    
    Use this when users ask about:
    - "What's the best season to fly at [site]?"
    - "When is [site] most flyable?"
    - "How many flying days per month at [site]?"
    - "Compare seasonal conditions at [site]"
    - "Is [site] good in winter/summer?"
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
    """Get weather-based flying forecasts for a specific paragliding site.
    
    This tool provides ML-powered predictions of flyability conditions based on weather
    forecasts. Shows probability of different flight performance levels for upcoming days.
    Forecasts are typically available for the next 7 days from today.
    
    Args:
        site_id: Unique identifier of the site (get from list_sites tool)
        query_date: Optional specific date to get forecast for, in 'YYYY-MM-DD' format
                   (e.g., '2024-03-15'). If not provided, returns all available forecasts.
    
    Returns:
        Dictionary with ISO dates ('YYYY-MM-DD') as keys, each containing probability
        predictions for different XC performance thresholds:
        - 'probability_of_flight_over_0XC_points_or_more': probability of any flyable conditions
        - 'probability_of_flight_over_10XC_points_or_more': probability of 10+ XC point flights
        - 'probability_of_flight_over_20XC_points_or_more': probability of 20+ XC point flights  
        - ... up to 'probability_of_flight_over_100XC_points_or_more'
        
        Probabilities range from 0.0 (impossible) to 1.0 (certain). Higher XC thresholds
        indicate better thermal conditions for cross-country flying.
    
    Use this when users ask about:
    - "What's the weather forecast for [site]?"
    - "Will it be flyable at [site] tomorrow?"
    - "Flying conditions for [site] this week"
    - "Probability of good thermals at [site]"
    - "Should I go to [site] on [specific date]?"
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


@mcp.tool()
async def get_site_takeoffs_and_landings(site_id: int) -> List[schemas.Spot]:
    """Get all takeoff and landing locations associated with a paragliding site.
    
    This tool provides detailed information about all launch and landing spots at a site,
    including their exact coordinates, elevation, directions, and characteristics.
    Essential for flight planning and understanding site layout.
    
    Args:
        site_id: Unique identifier of the site (get from list_sites tool)
    
    Returns:
        List of Spot objects containing detailed information for each takeoff/landing:
        - Coordinates (latitude/longitude) 
        - Elevation
        - Spot type (takeoff/landing)
        - Suitable wind direction
    
    Use this when users ask about:
    - "Where are the takeoffs at [site]?"
    - "Show me landing options for [site]"
    - "What are the coordinates of [site] launch points?"
    - "Which direction does [site] face?"
    - "How many takeoffs does [site] have?"
    - "Where can I land at [site]?"
    """
    async with AsyncSessionLocal() as db:
        spots_models = await crud.get_spots_by_site_id(db, site_id)
    
    adapter = TypeAdapter(List[schemas.Spot])
    spots = adapter.validate_python(spots_models)
    return spots


@mcp.tool()
async def plan_trip(
    start_date: str,
    end_date: str,
    metric: str = 'XC0',
    user_latitude: Optional[float] = None,
    user_longitude: Optional[float] = None,
    max_distance_km: Optional[float] = None,
    min_altitude_m: Optional[int] = None,
    max_altitude_m: Optional[int] = None,
    required_tags: Optional[List[str]] = None,
    offset: int = 0,
    limit: int = 10
) -> schemas.TripPlanResponse:
    """Find the best paragliding sites for a trip over a specific date range.
    
    This tool analyzes both weather forecasts (next 7 days) and historical flight data 
    to recommend paragliding sites with the highest flyability probability. Perfect for 
    planning paragliding trips, finding good flying conditions, or comparing sites.
    
    Args:
        start_date: Trip start date in 'YYYY-MM-DD' format (e.g., '2024-03-15')
        end_date: Trip end date in 'YYYY-MM-DD' format (e.g., '2024-03-20')
        metric: XC points threshold - 'XC0' for any flyable day, 'XC10' for 10+ XC points,
                up to 'XC100'. Higher thresholds = better/longer flight conditions.
        user_latitude: Your latitude in decimal degrees (e.g., 46.8182) to calculate distances
        user_longitude: Your longitude in decimal degrees (e.g., 8.2275) to calculate distances  
        max_distance_km: Only show sites within this distance from your location (kilometers)
        min_altitude_m: Minimum site altitude in meters (useful for avoiding low valleys)
        max_altitude_m: Maximum site altitude in meters (useful for avoiding extreme elevations)
        required_tags: List of required site characteristics. Common tags include:
                - 'car': takeoff accessible by car
                - 'lift': takeoff accessible by lift/chair or cable car  
                - 'shuttle': official shuttle service available
                - 'Alps': site located in the Alps
                - 'Pyrenees': site located in the Pyrenees
                - 'Appennines': site located in the Apennines
                - 'flats': site located in flatlands
                - 'mountaines': site located in mountains
        offset: Skip this many results (for pagination)
        limit: Maximum number of sites to return (default 10)
    
    Returns:
        Ranked list of sites with their average flyability probability, daily forecasts,
        coordinates, altitude, and distance from user location if provided. Sites are 
        sorted by flyability score (highest probability first).
    
    Use this when users ask about:
    - "Where should I fly next week?"
    - "Best sites for a 3-day paragliding trip"  
    - "Flying spots near [location] with good weather"
    - "Compare sites for specific dates"
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Dates must be in YYYY-MM-DD format")

    async with AsyncSessionLocal() as db:
        response = await trip_planner_service.plan_trip_service(
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
            limit=limit
        )

    return response
