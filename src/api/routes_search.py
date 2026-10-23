from fastapi import APIRouter, Query
from src.core.models import SearchResult
from src.services.external_api_service import api_service

router = APIRouter(prefix="/api/search", tags=["Location Search"])


@router.get("", response_model=list[SearchResult])
async def search_places(q: str = Query(..., min_length=1, description="Address, landmark, city, or coordinates")) -> list[SearchResult]:
    """Search for places, addresses, landmarks or raw coordinates worldwide."""
    return await api_service.search_locations(q)
