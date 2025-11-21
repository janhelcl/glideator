"""Site metadata utilities shared across Ground Crew components."""

import pandas as pd
from sqlalchemy.engine import Engine


def get_sites(engine: Engine) -> pd.DataFrame:
    """Return a DataFrame with all paragliding sites available in the mart."""
    query = """
    SELECT
        site_id,
        name,
        country
    FROM glideator_mart.dim_sites
    WHERE site_id <= 170 -- and site_id <= 248
    ORDER BY site_id
    """
    return pd.read_sql(query, engine)


def format_site_details(site_name: str, country: str, engine: Engine) -> str:
    """Format detailed site information including takeoffs and landings."""
    site_query = """
    SELECT site_id 
    FROM glideator_mart.dim_sites 
    WHERE name = %s AND country = %s
    LIMIT 1
    """

    try:
        site_result = pd.read_sql(site_query, engine, params=(site_name, country))
        if site_result.empty:
            return f"{site_name} ({country})"

        site_id = int(site_result.iloc[0]["site_id"])

        spots_query = """
        SELECT name, latitude, longitude, altitude, type, wind_direction
        FROM source.spots 
        WHERE site_id = %s
        ORDER BY type DESC, name, spot_id  -- takeoff first, then landing
        """

        spots_df = pd.read_sql(spots_query, engine, params=(site_id,))
        if spots_df.empty:
            return f"{site_name} ({country})"

        result: list[str] = [f"{site_name} ({country})"]

        takeoffs = spots_df[spots_df["type"] == "takeoff"]
        landings = spots_df[spots_df["type"] == "landing"]

        if not takeoffs.empty:
            result.append("Takeoffs:")
            for _, row in takeoffs.iterrows():
                coords = f"{row['latitude']:.6f}, {row['longitude']:.6f}"
                altitude = f"{row['altitude']}m" if pd.notna(row["altitude"]) else "N/A"
                wind_dir = row["wind_direction"] if pd.notna(row["wind_direction"]) else "N/A"
                result.append(f"    {row['name']}, {coords}, {altitude}, {wind_dir}")

        if not landings.empty:
            result.append("Landings:")
            for _, row in landings.iterrows():
                coords = f"{row['latitude']:.6f}, {row['longitude']:.6f}"
                altitude = f"{row['altitude']}m" if pd.notna(row["altitude"]) else "N/A"
                result.append(f"    {row['name']}, {coords}, {altitude}")

        return "\n".join(result)

    except Exception as exc:  # pragma: no cover - defensive fallback
        print(f"Warning: Could not fetch spot details for {site_name}: {exc}")
        return f"{site_name} ({country})"


