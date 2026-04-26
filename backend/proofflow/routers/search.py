from fastapi import APIRouter, HTTPException, Query, status

from proofflow.models.schemas import SearchResponse
from proofflow.services.search_service import SearchQueryError, search_chunks

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponse)
def search(q: str = Query(...), limit: int = Query(default=25, ge=1, le=25)) -> SearchResponse:
    try:
        return search_chunks(q, limit=limit)
    except SearchQueryError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
