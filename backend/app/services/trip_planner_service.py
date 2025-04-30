import datetime
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from collections import defaultdict

from .. import schemas, crud, models # Ensure crud and models are imported

def plan_trip_service(db: Session, start_date: datetime.date, end_date: datetime.date) -> List[schemas.SiteSuggestion]:
    """
    Core logic to query forecasts, aggregate data, rank sites.
    """
    
    # 1. Query XC0 predictions for the date range
    # Using the new crud function. Assumes it returns objects with site_id, date, value (for XC0)
    predictions = crud.get_predictions_for_range(db, start_date=start_date, end_date=end_date, metric='XC0')

    if not predictions:
        return [] # No predictions found for the range

    # 2. Aggregate per site
    site_data: Dict[int, Dict[str, Any]] = defaultdict(lambda: {'total_prob': 0.0, 'count': 0, 'flyable_days': 0, 'launch_name': 'Unknown'})
    
    site_ids_with_data = set()
    for p in predictions:
        # Assuming Prediction model has site_id (int) and value (float for the metric) 
        site_id = p.site_id 
        site_ids_with_data.add(site_id)
        
        # Aggregate XC0 probability (stored in 'value' based on metric filter)
        # Ensure p.value is the XC0 probability
        xc0_prob = p.value # Assuming the value column holds the probability for the 'XC0' metric
        if xc0_prob is not None: 
            site_data[site_id]['total_prob'] += xc0_prob
            site_data[site_id]['count'] += 1
            if xc0_prob >= 0.5:
                site_data[site_id]['flyable_days'] += 1
            
    # 3. Fetch site names
    sites_info = []
    if site_ids_with_data:
        # Use the new crud function. Assumes it returns Site objects with site_id and name
        sites_info = crud.get_sites_by_ids(db, site_ids=list(site_ids_with_data))
        
    # Create a map for easy lookup: site_id -> launch_name
    # Assumes Site model has 'name' attribute for the launch name
    site_name_map = {site.site_id: site.name for site in sites_info} 
    
    for site_id in site_data:
        site_data[site_id]['launch_name'] = site_name_map.get(site_id, f'Site ID: {site_id}') # Use Site ID if name not found
            
    # 4. Calculate averages and create SiteSuggestion objects
    suggestions = []
    for site_id, data in site_data.items():
        if data['count'] > 0:
            avg_flyability = data['total_prob'] / data['count']
            suggestions.append(
                schemas.SiteSuggestion(
                    site_id=str(site_id), # Schema expects string site_id
                    launch_name=data['launch_name'],
                    average_flyability=round(avg_flyability, 3), # Round for cleaner output
                    flyable_days=data['flyable_days']
                )
            )
        # Sites with prediction entries but no valid XC0 values (count == 0) are ignored
            
    # 5. Rank by average_flyability descending
    suggestions.sort(key=lambda s: s.average_flyability, reverse=True)
    
    # 6. Return top N (e.g., 10)
    TOP_N = 10
    return suggestions[:TOP_N]
    
    # return [] # Return empty list for now 