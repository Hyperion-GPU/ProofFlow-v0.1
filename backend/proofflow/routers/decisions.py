from fastapi import APIRouter, HTTPException, status

from proofflow.models.schemas import DecisionCreate, DecisionResponse, DecisionUpdate
from proofflow.services import decision_service
from proofflow.services.errors import NotFoundError

router = APIRouter(tags=["decisions"])


@router.get("/cases/{case_id}/decisions", response_model=list[DecisionResponse])
def list_case_decisions(case_id: str) -> list[DecisionResponse]:
    try:
        return decision_service.list_case_decisions(case_id)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post(
    "/cases/{case_id}/decisions",
    response_model=DecisionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_case_decision(case_id: str, payload: DecisionCreate) -> DecisionResponse:
    try:
        return decision_service.create_decision(case_id, payload)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.patch("/decisions/{decision_id}", response_model=DecisionResponse)
def update_decision(decision_id: str, payload: DecisionUpdate) -> DecisionResponse:
    if not payload.model_fields_set:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="no fields provided",
        )
    try:
        return decision_service.update_decision(decision_id, payload)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
