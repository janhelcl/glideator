import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import schemas # Removed crud, models imports (handled by service)
from ..database import SessionLocal
from ..services import trip_planner_service # Import the service

router = APIRouter()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/plan-trip", response_model=schemas.TripPlanResponse)
def plan_trip_endpoint(
    request: schemas.TripPlanRequest,
    db: Session = Depends(get_db)
):
    """
    Suggests the best individual sites based on aggregated flyability forecast 
    over a given date range.
    """
    
    # TODO: Input Validation (date range, max span)
    if request.start_date > request.end_date:
        raise HTTPException(status_code=400, detail="Start date cannot be after end date.")
    
    # Limit date range (e.g., max 14 days for now)
    # max_days = 14 
    # if (request.end_date - request.start_date).days + 1 > max_days:
    #     raise HTTPException(status_code=400, detail=f"Date range cannot exceed {max_days} days.")

    
    # Call Core Logic Service function
    site_suggestions = trip_planner_service.plan_trip_service(
        db=db, start_date=request.start_date, end_date=request.end_date
    )
    
    # Handle case where service returns empty list (e.g., no data)
    # The design doc specified 200 OK with empty list, so no extra check needed here
    # unless we want a specific 404, but let's stick to the doc for now.

    return schemas.TripPlanResponse(sites=site_suggestions)

# Placeholder function REMOVED 