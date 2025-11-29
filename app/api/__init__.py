"""
API routes for the search functionality.
"""

from fastapi import APIRouter, HTTPException, Query
from app.core.logging import logger
from app.schemas import SearchQuery, SearchResponse, HealthCheckResponse
from app.services import search_service
from app.exceptions import SearchException, ExternalAPIError
from app.core.config import settings

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint.
    
    Returns:
        Health check response with status and version
    """
    logger.info("Health check requested")
    return HealthCheckResponse(
        status="healthy",
        version=settings.APP_VERSION
    )


@router.post("/search", response_model=SearchResponse)
async def search(
    query: str = Query(..., min_length=1, max_length=500, description="Search query"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results")
) -> SearchResponse:
    """
    Search endpoint.
    
    Args:
        query: Search query string
        skip: Number of results to skip (default: 0)
        limit: Maximum number of results (default: 10, max: 100)
    
    Returns:
        Search response with results and metadata
    
    Raises:
        HTTPException: If search operation fails
    """
    try:
        logger.info(f"Search request: query='{query}'")
        
        results, total = await search_service.search(query, skip, limit)
        
        return SearchResponse(
            query=query,
            total=total,
            skip=skip,
            limit=limit,
            results=results
        )
    
    except SearchException as e:
        logger.error(f"Search error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    
    except ExternalAPIError as e:
        logger.error(f"External API error: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
