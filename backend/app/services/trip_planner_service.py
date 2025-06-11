import datetime
import calendar
import math
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Tuple, Literal, Optional
from collections import defaultdict

from .. import schemas, crud, models # Ensure crud and models are imported


TOP_N = 10


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth using the Haversine formula.
    
    Args:
        lat1, lon1: Latitude and longitude of first point in decimal degrees
        lat2, lon2: Latitude and longitude of second point in decimal degrees
    
    Returns:
        Distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of Earth in kilometers
    r = 6371
    
    return c * r


def get_flight_stats_attr_for_metric(metric: str) -> str:
    """Maps metric name to the corresponding FlightStats attribute name."""
    metric_to_attr = {
        'XC0': 'avg_days_over_0',
        'XC10': 'avg_days_over_10', 
        'XC20': 'avg_days_over_20',
        'XC30': 'avg_days_over_30',
        'XC40': 'avg_days_over_40',
        'XC50': 'avg_days_over_50',
        'XC60': 'avg_days_over_60',
        'XC70': 'avg_days_over_70',
        'XC80': 'avg_days_over_80',
        'XC90': 'avg_days_over_90',
        'XC100': 'avg_days_over_100'
    }
    return metric_to_attr.get(metric, 'avg_days_over_0')

def get_historical_prob(flight_stats: models.FlightStats, year: int, month: int, metric: str) -> float:
    """Calculates historical flyability probability from FlightStats for the given metric."""
    days_in_month = calendar.monthrange(year, month)[1]
    
    # Get the appropriate attribute based on the metric
    attr_name = get_flight_stats_attr_for_metric(metric)
    avg_flyable_days = getattr(flight_stats, attr_name, 0.0)
    
    return (avg_flyable_days / days_in_month) if days_in_month > 0 else 0

def plan_trip_service(
    db: Session, 
    start_date: datetime.date, 
    end_date: datetime.date, 
    metric: str = 'XC0',
    user_latitude: Optional[float] = None,
    user_longitude: Optional[float] = None,
    max_distance_km: Optional[float] = None
) -> List[schemas.SiteSuggestion]:
    """
    Core logic to query forecasts and historical stats, aggregate data, and rank sites.
    """
    # --- 1. Define Date Ranges & Fetch Data ---
    
    today = datetime.date.today()
    forecast_horizon = today + datetime.timedelta(days=7)

    forecast_start_date = max(start_date, today)
    forecast_end_date = min(end_date, forecast_horizon)
    
    predictions = []
    if forecast_start_date <= forecast_end_date:
        predictions = crud.get_predictions_for_range(
            db, start_date=forecast_start_date, end_date=forecast_end_date, metric=metric
        )

    all_flight_stats = crud.get_all_flight_stats(db)
    all_sites = crud.get_sites(db, skip=0, limit=1000)  # Get all sites with coordinates

    if not all_sites:
        return []

    # --- 2. Pre-process Data into Lookup Maps ---

    pred_map = {(p.site_id, p.date): p.value for p in predictions}
    stats_map: Dict[Tuple[int, int], float] = {}
    
    unique_months = set()
    d = start_date
    while d <= end_date:
        unique_months.add((d.year, d.month))
        d = (d.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)

    for stat in all_flight_stats:
        for year, month in unique_months:
            if stat.month == month:
                prob = get_historical_prob(stat, year, month, metric)
                stats_map[(stat.site_id, month)] = prob

    site_name_map = {site.site_id: site.name for site in all_sites}
    site_lat_map = {site.site_id: site.latitude for site in all_sites}
    site_lon_map = {site.site_id: site.longitude for site in all_sites}

    # --- 3. Aggregate Probabilities Per Site ---

    site_data: Dict[int, Dict[str, Any]] = defaultdict(lambda: {'total_prob': 0.0, 'count': 0, 'daily_probs': []})
    
    current_date = start_date
    while current_date <= end_date:
        for site_id, site_name in site_name_map.items():
            prob = pred_map.get((site_id, current_date))
            source: Literal['forecast', 'historical'] = 'forecast'

            if prob is None:
                prob = stats_map.get((site_id, current_date.month), 0.0)
                source = 'historical'

            site_data[site_id]['total_prob'] += prob
            site_data[site_id]['count'] += 1
            site_data[site_id]['daily_probs'].append(
                schemas.DailyProbability(date=current_date, probability=prob, source=source)
            )
        
        current_date += datetime.timedelta(days=1)

    # --- 4. Format and Rank Results ---
    
    suggestions = []
    for site_id, data in site_data.items():
        if data['count'] > 0:
            site_lat = site_lat_map.get(site_id, 0.0)
            site_lon = site_lon_map.get(site_id, 0.0)
            
            # Calculate distance if user location is provided
            distance_km = None
            if user_latitude is not None and user_longitude is not None:
                distance_km = calculate_distance_km(user_latitude, user_longitude, site_lat, site_lon)
                
                # Apply distance filtering if max distance is also provided
                if max_distance_km is not None and max_distance_km > 0:
                    if distance_km > max_distance_km:
                        continue  # Skip sites beyond max distance
            
            avg_flyability = data['total_prob'] / data['count']
            suggestions.append(
                schemas.SiteSuggestion(
                    site_id=str(site_id),
                    site_name=site_name_map.get(site_id, f'Site ID: {site_id}'),
                    latitude=site_lat,
                    longitude=site_lon,
                    average_flyability=round(avg_flyability, 3),
                    daily_probabilities=data['daily_probs'],
                    distance_km=round(distance_km, 1) if distance_km is not None else None
                )
            )

    suggestions.sort(key=lambda s: s.average_flyability, reverse=True)
    
    return suggestions[:TOP_N]