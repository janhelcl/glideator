import re
import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import date
from collections import defaultdict

from .. import crud
from ..database import AsyncSessionLocal

router = APIRouter(
    tags=["llms"],
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


def strip_html_tags(html_text: str) -> str:
    """Remove HTML tags and clean up text for plain markdown output."""
    if not html_text:
        return ""
    
    # Remove <body> tags
    text = re.sub(r'<body>|</body>', '', html_text)
    
    # Convert <h2> to ## markdown headers
    text = re.sub(r'<h2>(.*?)</h2>', r'## \1', text)
    
    # Convert <strong> to **bold**
    text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text)
    
    # Convert <a href="...">text</a> to [text](url)
    text = re.sub(r'<a href="(.*?)">(.*?)</a>', r'[\2](\1)', text)
    
    # Convert list items
    text = re.sub(r'<li>(.*?)</li>', r'- \1', text)
    
    # Remove remaining HTML tags
    text = re.sub(r'<ul>|</ul>|<p>|</p>', '\n', text)
    
    # Clean up excessive newlines
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    # Clean up leading/trailing whitespace
    text = text.strip()
    
    return text


def format_predictions(predictions: List) -> str:
    """Format prediction data as readable markdown."""
    if not predictions:
        return "No forecast data available."
    
    lines = []
    
    # Group predictions by date
    predictions_by_date = defaultdict(lambda: {'metrics': {}, 'computed_at': None, 'gfs_forecast_at': None})
    for pred in predictions:
        predictions_by_date[pred.date]['metrics'][pred.metric] = pred.value
        predictions_by_date[pred.date]['computed_at'] = pred.computed_at
        predictions_by_date[pred.date]['gfs_forecast_at'] = pred.gfs_forecast_at
    
    # Get the most recent timestamp
    latest_computed = None
    for date_data in predictions_by_date.values():
        if date_data['computed_at']:
            if not latest_computed or date_data['computed_at'] > latest_computed:
                latest_computed = date_data['computed_at']
    
    if latest_computed:
        lines.append(f"*Predictions computed at: {latest_computed.strftime('%Y-%m-%d %H:%M UTC')}*\n")
    
    # Sort by date and format
    for prediction_date in sorted(predictions_by_date.keys()):
        data = predictions_by_date[prediction_date]
        metrics = data['metrics']
        
        # Format the date nicely
        date_str = prediction_date.strftime('%Y-%m-%d (%A)')
        
        # Build metrics string
        metric_strs = []
        for metric_name in ['XC0', 'XC10', 'XC20', 'XC30', 'XC40', 'XC50', 'XC60', 'XC70', 'XC80', 'XC90', 'XC100']:
            if metric_name in metrics:
                value = metrics[metric_name]
                metric_strs.append(f"{metric_name}: {value:.1%}")
        
        lines.append(f"**{date_str}**")
        lines.append("  " + ", ".join(metric_strs))
        lines.append("")
    
    return "\n".join(lines)


def format_flight_stats(flight_stats: List) -> str:
    """Format seasonal flight statistics by month."""
    if not flight_stats:
        return "No seasonal statistics available."
    
    # Assuming flight_stats is ordered by month (1-12)
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    
    lines = []
    lines.append("Average number of days per month with flights exceeding distance thresholds:\n")
    
    for i, stat in enumerate(flight_stats[:12]):  # Ensure we only take 12 months
        month_name = month_names[i] if i < len(month_names) else f"Month {i+1}"
        
        # Format with key thresholds
        lines.append(f"**{month_name}**")
        lines.append(f"  - Any flight (>0 XC points): {stat.avg_days_over_0:.1f} days")
        lines.append(f"  - flight >10 XC points: {stat.avg_days_over_10:.1f} days")
        lines.append(f"  - flight >20 XC points: {stat.avg_days_over_20:.1f} days")
        lines.append(f"  - flight >30 XC points: {stat.avg_days_over_30:.1f} days")
        lines.append(f"  - flight >40 XC points: {stat.avg_days_over_40:.1f} days")
        lines.append(f"  - flight >50 XC points: {stat.avg_days_over_50:.1f} days")
        lines.append(f"  - flight >60 XC points: {stat.avg_days_over_60:.1f} days")
        lines.append(f"  - flight >70 XC points: {stat.avg_days_over_70:.1f} days")
        lines.append(f"  - flight >80 XC points: {stat.avg_days_over_80:.1f} days")
        lines.append(f"  - flight >90 XC points: {stat.avg_days_over_90:.1f} days")
        lines.append(f"  - flight >100 XC points: {stat.avg_days_over_100:.1f} days")
        lines.append("")
    
    return "\n".join(lines)


def format_spots(spots: List) -> str:
    """Format takeoff and landing spots information."""
    if not spots:
        return "No takeoff/landing spot information available."
    
    lines = []
    
    takeoffs = [s for s in spots if s.type == 'takeoff']
    landings = [s for s in spots if s.type == 'landing']
    
    if takeoffs:
        lines.append("### Takeoff Spots\n")
        for spot in takeoffs:
            lines.append(f"**{spot.name}**")
            lines.append(f"- Coordinates: {spot.latitude:.5f}, {spot.longitude:.5f}")
            if spot.altitude:
                lines.append(f"- Altitude: {spot.altitude}m")
            if spot.wind_direction:
                lines.append(f"- Wind Direction: {spot.wind_direction}")
            lines.append("")
    
    if landings:
        lines.append("### Landing Spots\n")
        for spot in landings:
            lines.append(f"**{spot.name}**")
            lines.append(f"- Coordinates: {spot.latitude:.5f}, {spot.longitude:.5f}")
            if spot.altitude:
                lines.append(f"- Altitude: {spot.altitude}m")
            lines.append("")
    
    return "\n".join(lines)


@router.get("/llms.txt", response_class=Response)
async def get_main_llms_txt(db: AsyncSession = Depends(get_db)):
    """
    Main llms.txt file with overview and directory of all sites.
    Explicitly allows AI/bot access with permissive headers.
    """
    # Static content embedded directly
    static_content = """# Parra-Glideator

> Parra-Glideator is your AI-powered paragliding companion that helps pilots find the perfect place and time to fly. Using machine learning and weather forecasting, it recommends optimal flying spots and conditions based on current weather forecast and historical flight patterns from 250 most popular paragliding sites in Europe.

Parra-Glideator combines advanced weather prediction with pilot-friendly tools to make paragliding safer, smarter, and more enjoyable. Whether you're planning your next flight or exploring new sites, our AI-powered recommendations help you make informed decisions about when and where to fly.

## Main Features

- **Interactive Map**: Browse 250 paragliding european sites with detailed information, takeoff/landing coordinates, facilities, and local conditions
- **Site Details**: Get comprehensive information about each flying site including wind directions, best flying seasons, difficulty levels, and safety considerations  
- **Trip Planning**: Plan multi-day paragliding trips with personalized recommendations based on your dates, skill level, and weather preferences
- **Weather Forecasting**: Access 7-day flying forecasts powered by machine learning models that analyze NOAA weather data and historical flight patterns

## How to Use Parra-Glideator

- **Explore the Map**: Visit the main map to discover paragliding sites near you or in your destination area. Click on any site marker to see detailed information, photos, and current conditions
- **Check Site Details**: Each site page provides everything you need to know - wind directions, seasonal patterns, difficulty ratings, nearby amenities, and safety information
- **Plan Your Trip**: Use the trip planner to find the best sites for your travel dates. Filter by skill level, preferred weather conditions, and site amenities to create your perfect paragliding adventure
- **Get Weather Forecasts**: View detailed flying forecasts that combine meteorological data with machine learning predictions to tell you the likelihood of good flying conditions

## AI-Powered Forecasting

Our forecasting system analyzes real-time weather data from NOAA's Global Forecast System combined with historical flight data from thousands of pilots. The machine learning models learn from actual flight patterns to predict not just what the weather will be, but whether conditions will be suitable for paragliding at each specific site.

The forecast considers factors like:
- Wind speed and direction at different altitudes
- Thermal activity and lift potential  
- Weather stability and safety conditions
- Historical success rates for similar conditions

## Connect Your AI Assistant

Parra-Glideator provides a Model Context Protocol (MCP) server that allows you to connect AI assistants like Claude or ChatGPT to access paragliding data. Your AI assistant can help you:
- Find suitable flying sites based on your criteria
- Check weather forecasts and flying conditions
- Plan paragliding trips and itineraries
- Get detailed site information and safety advice

To connect your AI assistant, use the MCP server at: `https://www.parra-glideator.com/mcp`
"""
    
    # Fetch all sites
    sites = await crud.get_site_list(db)
    
    # Build the site directory
    site_directory = ["\n\n## Site Directory\n"]
    site_directory.append("All paragliding sites with detailed information, current flyibility forecasts for next 7 days, and seasonal flying statistics:\n")
    site_directory.append("Use these links answer questions such as:")
    site_directory.append("What is the best time of the year to fly at <site_name>?")
    site_directory.append("Is it flyable today at <site_name>?")
    site_directory.append("What is the probability of flying more than <XC_points> XC points at <site_name> on <date>?")
    site_directory.append("What is a better place to fly on <date> <site_name_1> or <site_name_2>?\n")
    
    # Use /api/ path which proxies through frontend domain (avoids bot blocking)
    for site in sites:
        site_id = site[0]  # site_id
        site_name = site[1]  # name
        site_directory.append(f"- [{site_name}](https://www.parra-glideator.com/api/llms/sites/{site_id}.txt)")
    
    # Combine everything
    content = static_content + "\n".join(site_directory)
    
    # Return with headers that explicitly allow AI/bot access
    return Response(
        content=content, 
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=300",  # Cache for 5 minutes
            "X-Robots-Tag": "all",  # Explicitly allow bots
            "Access-Control-Allow-Origin": "*",  # Allow cross-origin requests
        }
    )


@router.get("/llms/sites/{site_id}.txt", response_class=Response)
async def get_site_llms_txt(site_id: int, db: AsyncSession = Depends(get_db)):
    """
    Detailed information about a specific paragliding site in LLM-friendly format.
    Explicitly allows AI/bot access with permissive headers.
    """
    # Fetch site basic info
    site = await crud.get_site(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site with ID {site_id} not found")
    
    # Fetch site detailed info
    try:
        site_info = await crud.get_site_info(db, site_id)
    except:
        site_info = None
    
    # Fetch tags
    tags = await crud.get_tags_by_site_id(db, site_id)
    
    # Fetch predictions
    predictions = await crud.get_predictions(db, site_id, query_date=None, metric=None)
    
    # Fetch flight stats
    flight_stats = await crud.get_flight_stats_by_site_id(db, site_id)
    
    # Fetch spots
    spots = await crud.get_spots_by_site_id(db, site_id)
    
    # Build the markdown content
    lines = []
    
    # Title
    country = site_info.country if site_info else "Unknown"
    lines.append(f"# {site.name} ({country})\n")
    
    # Location
    lines.append("## Location\n")
    lines.append(f"- **Latitude**: {site.latitude:.5f}")
    lines.append(f"- **Longitude**: {site.longitude:.5f}")
    lines.append(f"- **Altitude**: {site.altitude}m")
    lines.append(f"- **Site ID**: {site.site_id}\n")
    
    # Tags
    if tags:
        lines.append("## Tags\n")
        lines.append(", ".join(tags) + "\n")
    
    # Description from site_info
    if site_info and site_info.html:
        lines.append("## Site Information\n")
        cleaned_text = strip_html_tags(site_info.html)
        lines.append(cleaned_text)
        lines.append("")
    
    # Current 7-Day Forecast
    lines.append("## Current 7-Day Forecast\n")
    lines.append("Glideator ML predictions for flying conditions (probability of achieving XC distance):\n")
    lines.append("Metric explanation: 'XC0' for any flyable day, 'XC10' for 10+ XC points, up to 'XC100'. Higher thresholds = better/longer flight conditions.\n")
    forecast_text = format_predictions(predictions)
    lines.append(forecast_text)
    
    # Seasonal Flying Statistics
    if flight_stats:
        lines.append("\n## Seasonal Flying Statistics\n")
        stats_text = format_flight_stats(flight_stats)
        lines.append(stats_text)
    
    # Takeoff & Landing Spots
    if spots:
        lines.append("\n## Takeoff & Landing Spots\n")
        spots_text = format_spots(spots)
        lines.append(spots_text)
    
    # Footer with link back
    lines.append("\n---")
    lines.append(f"\n*For more information and interactive maps, visit: https://www.parra-glideator.com/details/{site_id}*")
    
    content = "\n".join(lines)
    
    # Return with headers that explicitly allow AI/bot access
    return Response(
        content=content, 
        media_type="text/plain; charset=utf-8",
        headers={
            "Cache-Control": "public, max-age=300",  # Cache for 5 minutes (forecasts update every few hours)
            "X-Robots-Tag": "all",  # Explicitly allow bots
            "Access-Control-Allow-Origin": "*",  # Allow cross-origin requests
            "Content-Disposition": "inline",  # Ensure browsers display, not download
        }
    )

