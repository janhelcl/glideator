from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date

from .. import schemas, crud
from ..database import AsyncSessionLocal

router = APIRouter(
    prefix="/d2d",
    tags=["data-to-date"],
    responses={404: {"description": "Not found"}},
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


@router.get("/similar-days/{site_id}/{forecast_date}", response_model=schemas.SimilarDaysResponse)
async def get_similar_days(
    site_id: int,
    forecast_date: date,
    n: Optional[int] = Query(None, description="Number of similar days to return (defaults to D2D_SIMILAR_DAYS_K env var)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get N most similar past dates for a given site_id and forecast_date.
    
    Returns a list of past dates with their similarity scores, ordered by similarity (highest first).
    """
    # Validate site exists
    site = await crud.get_site(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site with ID {site_id} not found")
    
    # Get similar dates
    similar_dates = await crud.get_similar_dates(db, site_id, forecast_date)
    
    # If n is specified, limit results
    if n is not None:
        similar_dates = similar_dates[:n]
    
    # Convert to response format
    similar_days = [
        schemas.SimilarDayItem(
            past_date=sd.past_date,
            similarity=sd.similarity
        )
        for sd in similar_dates
    ]
    
    return schemas.SimilarDaysResponse(
        site_id=site_id,
        forecast_date=forecast_date,
        similar_days=similar_days
    )


@router.get("/past-forecast/{site_id}/{forecast_date}/{past_date}", response_model=schemas.PastDateForecastResponse)
async def get_past_date_forecast(
    site_id: int,
    forecast_date: date,
    past_date: date,
    db: AsyncSession = Depends(get_db)
):
    """
    Get the forecast data for a specific past_date that was identified as similar
    to the forecast_date for the given site_id.
    
    Returns the full forecast data (forecast_9, forecast_12, forecast_15) along with metadata.
    """
    # Validate site exists
    site = await crud.get_site(db, site_id)
    if not site:
        raise HTTPException(status_code=404, detail=f"Site with ID {site_id} not found")
    
    # Get past date forecast from similar_dates table
    similar_date = await crud.get_past_date_forecast(db, site_id, forecast_date, past_date)
    
    if not similar_date:
        raise HTTPException(
            status_code=404,
            detail=f"No similar date record found for site_id={site_id}, forecast_date={forecast_date}, past_date={past_date}"
        )
    
    # Convert to response format
    return schemas.PastDateForecastResponse(
        site_id=similar_date.site_id,
        forecast_date=similar_date.forecast_date,
        past_date=similar_date.past_date,
        similarity=similar_date.similarity,
        forecast_9=similar_date.forecast_9,
        forecast_12=similar_date.forecast_12,
        forecast_15=similar_date.forecast_15
    )

