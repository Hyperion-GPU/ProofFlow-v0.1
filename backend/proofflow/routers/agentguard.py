from fastapi import APIRouter, HTTPException, status

from proofflow.models.schemas import AgentGuardReviewRequest, AgentGuardReviewResponse
from proofflow.services.git_service import GitServiceError
from proofflow.services.review_service import ReviewServiceError, review_repository

router = APIRouter(prefix="/agentguard", tags=["agentguard"])


@router.post("/review", response_model=AgentGuardReviewResponse)
def review_local_repository(payload: AgentGuardReviewRequest) -> AgentGuardReviewResponse:
    try:
        return review_repository(payload)
    except (GitServiceError, ReviewServiceError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
