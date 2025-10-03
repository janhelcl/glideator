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
        lines.append(f"  - Any XC flight (>0km): {stat.avg_days_over_0:.1f} days")
        lines.append(f"  - XC >20km: {stat.avg_days_over_20:.1f} days")
        lines.append(f"  - XC >50km: {stat.avg_days_over_50:.1f} days")
        lines.append(f"  - XC >100km: {stat.avg_days_over_100:.1f} days")
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


@router.get("/llms.txt")
async def get_main_llms_txt(db: AsyncSession = Depends(get_db)):
    """
    Main llms.txt file with overview and directory of all sites.
    """
    # Read the static content from frontend/public/llms.txt
    static_file_path = os.path.join(
        os.path.dirname(__file__), 
        '..', '..', '..', 
        'frontend', 'public', 'llms.txt'
    )
    
    try:
        with open(static_file_path, 'r', encoding='utf-8') as f:
            static_content = f.read()
    except FileNotFoundError:
        # Fallback if file not found
        static_content = "# Parra-Glideator\n\nAI-powered paragliding site recommendations.\n"
    
    # Fetch all sites
    sites = await crud.get_site_list(db)
    
    # Build the site directory
    site_directory = ["\n\n## Site Directory\n"]
    site_directory.append("All paragliding sites with detailed information, current forecasts, and seasonal statistics:\n")
    
    for site in sites:
        site_id = site[0]  # site_id
        site_name = site[1]  # name
        site_directory.append(f"- [{site_name}](/llms/sites/{site_id}.txt)")
    
    # Combine everything
    content = static_content + "\n".join(site_directory)
    
    return Response(content=content, media_type="text/plain; charset=utf-8")


@router.get("/llms/sites/{site_id}.txt")
async def get_site_llms_txt(site_id: int, db: AsyncSession = Depends(get_db)):
    """
    Detailed information about a specific paragliding site in LLM-friendly format.
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
    
    return Response(content=content, media_type="text/plain; charset=utf-8")

