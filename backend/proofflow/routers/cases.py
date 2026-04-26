from fastapi import APIRouter, HTTPException, status

from proofflow.models.schemas import (
    CaseCreate,
    CaseDetailResponse,
    CasePacketResponse,
    CaseResponse,
    CaseUpdate,
)
from proofflow.services import case_packet_service, case_service
from proofflow.services.errors import NotFoundError

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("", response_model=list[CaseResponse])
def list_cases() -> list[CaseResponse]:
    return case_service.list_cases()


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(payload: CaseCreate) -> CaseResponse:
    return case_service.create_case(payload)


@router.get("/{case_id}/packet", response_model=CasePacketResponse)
def get_case_packet(case_id: str) -> CasePacketResponse:
    try:
        return case_packet_service.get_case_packet(case_id)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_case(case_id: str) -> CaseDetailResponse:
    try:
        return case_service.get_case_detail(case_id)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(case_id: str, payload: CaseUpdate) -> CaseResponse:
    if not payload.model_fields_set:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="no fields provided",
        )
    try:
        return case_service.update_case(case_id, payload)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
