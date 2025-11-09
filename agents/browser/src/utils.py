from datetime import datetime

import pandas as pd
from typing import Dict


def get_current_date():
    """Get current date in a readable format."""
    return datetime.now().strftime("%B %d, %Y")


def get_sites(engine):
    """Return a DataFrame with *all* paragliding sites available in the mart.

    Adjust the SQL query if you need to filter the list (e.g. by country).
    """
    query = """
    SELECT
        site_id,
        name,
        country
    FROM glideator_mart.dim_sites
    WHERE site_id > 133 and site_id <= 251
    ORDER BY site_id
    """
    return pd.read_sql(query, engine)


def format_site_details(site_name: str, country: str, engine) -> str:
    """Format detailed site information including takeoffs and landings.
    
    Args:
        site_name: Name of the site
        country: Country where the site is located
        engine: Database engine for querying spot data
        
    Returns:
        Formatted string with site name, country, takeoffs, and landings
    """
    # Get site_id from the site name and country
    site_query = """
    SELECT site_id 
    FROM glideator_mart.dim_sites 
    WHERE name = %s AND country = %s
    LIMIT 1
    """
    
    try:
        site_result = pd.read_sql(site_query, engine, params=(site_name, country))
        if site_result.empty:
            # Fallback to just site name and country if no spots found
            return f"{site_name} ({country})"
            
        site_id = int(site_result.iloc[0]['site_id'])
        
        # Get takeoffs and landings for this site
        spots_query = """
        SELECT name, latitude, longitude, altitude, type, wind_direction
        FROM source.spots 
        WHERE site_id = %s
        ORDER BY type DESC, name, spot_id  -- takeoff first, then landing
        """
        
        spots_df = pd.read_sql(spots_query, engine, params=(site_id,))
        
        if spots_df.empty:
            # Fallback if no spots data available
            return f"{site_name} ({country})"
            
        # Format the output
        result = [f"{site_name} ({country})"]
        
        # Group by type
        takeoffs = spots_df[spots_df['type'] == 'takeoff']
        landings = spots_df[spots_df['type'] == 'landing']
        
        if not takeoffs.empty:
            result.append("Takeoffs:")
            for _, row in takeoffs.iterrows():
                coords = f"{row['latitude']:.6f}, {row['longitude']:.6f}"
                altitude = f"{row['altitude']}m" if pd.notna(row['altitude']) else "N/A"
                wind_dir = row['wind_direction'] if pd.notna(row['wind_direction']) else "N/A"
                result.append(f"    {row['name']}, {coords}, {altitude}, {wind_dir}")
        
        if not landings.empty:
            result.append("Landings:")
            for _, row in landings.iterrows():
                coords = f"{row['latitude']:.6f}, {row['longitude']:.6f}"
                altitude = f"{row['altitude']}m" if pd.notna(row['altitude']) else "N/A"
                result.append(f"    {row['name']}, {coords}, {altitude}")
                
        return "\n".join(result)
        
    except Exception as e:
        # Fallback to simple format if there's any error
        print(f"Warning: Could not fetch spot details for {site_name}: {e}")
        return f"{site_name} ({country})"