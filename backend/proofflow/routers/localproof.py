from fastapi import APIRouter, HTTPException, status

from proofflow.models.schemas import (
    LocalProofScanRequest,
    LocalProofScanSummary,
    LocalProofSuggestActionsRequest,
    LocalProofSuggestActionsSummary,
)
from proofflow.services.action_suggestion_service import (
    SuggestActionsError,
    suggest_actions,
)
from proofflow.services.errors import NotFoundError
from proofflow.services.file_scanner import ScanPathError, scan_folder

router = APIRouter(prefix="/localproof", tags=["localproof"])


@router.post("/scan", response_model=LocalProofScanSummary)
def scan_local_folder(payload: LocalProofScanRequest) -> LocalProofScanSummary:
    try:
        return scan_folder(payload)
    except ScanPathError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/suggest-actions", response_model=LocalProofSuggestActionsSummary)
def suggest_localproof_actions(
    payload: LocalProofSuggestActionsRequest,
) -> LocalProofSuggestActionsSummary:
    try:
        return suggest_actions(payload)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except SuggestActionsError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
