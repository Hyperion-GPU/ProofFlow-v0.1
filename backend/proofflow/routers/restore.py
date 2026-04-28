from fastapi import APIRouter, HTTPException, status

from proofflow.models.schemas import (
    RestorePreviewRequest,
    RestorePreviewResponse,
    RestoreToNewLocationRequest,
    RestoreToNewLocationResponse,
)
from proofflow.services import restore_service
from proofflow.services.errors import NotFoundError
from proofflow.services.restore_service import RestoreError

router = APIRouter(prefix="/restore", tags=["restore"])


@router.post("/preview", response_model=RestorePreviewResponse)
def preview_restore(payload: RestorePreviewRequest) -> RestorePreviewResponse:
    try:
        return restore_service.preview_restore(payload)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RestoreError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/to-new-location", response_model=RestoreToNewLocationResponse)
def restore_to_new_location(payload: RestoreToNewLocationRequest) -> RestoreToNewLocationResponse:
    try:
        return restore_service.restore_to_new_location(payload)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except RestoreError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
