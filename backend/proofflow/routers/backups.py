from fastapi import APIRouter, HTTPException, status

from proofflow.models.schemas import (
    BackupCreateRequest,
    BackupCreateResponse,
    BackupDetailResponse,
    BackupListResponse,
    BackupPreviewRequest,
    BackupPreviewResponse,
    BackupVerifyRequest,
    BackupVerifyResponse,
)
from proofflow.services import backup_service
from proofflow.services.backup_service import BackupError
from proofflow.services.errors import NotFoundError

router = APIRouter(prefix="/backups", tags=["backups"])


@router.post("/preview", response_model=BackupPreviewResponse)
def preview_backup(payload: BackupPreviewRequest) -> BackupPreviewResponse:
    try:
        return backup_service.preview_backup(payload)
    except BackupError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("", response_model=BackupCreateResponse, status_code=status.HTTP_201_CREATED)
def create_backup(payload: BackupCreateRequest) -> BackupCreateResponse:
    try:
        return backup_service.create_backup(payload)
    except BackupError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.get("", response_model=BackupListResponse)
def list_backups() -> BackupListResponse:
    return backup_service.list_backups()


@router.get("/{backup_id}", response_model=BackupDetailResponse)
def get_backup(backup_id: str) -> BackupDetailResponse:
    try:
        return backup_service.get_backup(backup_id)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/{backup_id}/verify", response_model=BackupVerifyResponse)
def verify_backup(backup_id: str, payload: BackupVerifyRequest) -> BackupVerifyResponse:
    try:
        return backup_service.verify_backup(backup_id, payload)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except BackupError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
