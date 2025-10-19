from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .. import schemas, crud
from ..database import AsyncSessionLocal
from ..services.s2s_recommender import vector_search

router = APIRouter(
    prefix="/s2s",
    tags=["site-to-site"],
    responses={404: {"description": "Not found"}},
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.post("/recommendations", response_model=schemas.S2SRecommendationResponse)
async def get_site_recommendations(
    request: schemas.S2SRecommendationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Get site-to-site recommendations based on learned embeddings.
    Finds sites similar to the provided source site IDs using vector similarity.
    """
    # Validate that all source sites exist
    for site_id in request.source_site_ids:
        site = await crud.get_site(db, site_id)
        if not site:
            raise HTTPException(
                status_code=404, 
                detail=f"Site with ID {site_id} not found"
            )
    
    # Get recommendations using the vector search
    recommendations = vector_search(request.source_site_ids, top_k=request.top_k)
    
    if recommendations is None:
        # No valid source sites found in embeddings
        return schemas.S2SRecommendationResponse(
            recommendations=[],
            total_found=0
        )
    
    # Convert to response format
    recommendation_items = [
        schemas.S2SRecommendationItem(
            site_id=site_id,
            similarity_score=score
        )
        for site_id, score in recommendations
    ]
    
    return schemas.S2SRecommendationResponse(
        recommendations=recommendation_items,
        total_found=len(recommendation_items)
    )

@router.get("/recommendations/{site_id}", response_model=schemas.S2SRecommendationResponse)
async def get_site_recommendations_single(
    site_id: int,
    top_k: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """
    Get site-to-site recommendations for a single site.
    Convenience endpoint for single site recommendations.
    """
    # Validate that the site exists
    site = await crud.get_site(db, site_id)
    if not site:
        raise HTTPException(
            status_code=404, 
            detail=f"Site with ID {site_id} not found"
        )
    
    # Get recommendations using the vector search
    recommendations = vector_search([site_id], top_k=top_k)
    
    if recommendations is None:
        # No valid source sites found in embeddings
        return schemas.S2SRecommendationResponse(
            recommendations=[],
            total_found=0
        )
    
    # Convert to response format
    recommendation_items = [
        schemas.S2SRecommendationItem(
            site_id=rec_site_id,
            similarity_score=score
        )
        for rec_site_id, score in recommendations
    ]
    
    return schemas.S2SRecommendationResponse(
        recommendations=recommendation_items,
        total_found=len(recommendation_items)
    )
