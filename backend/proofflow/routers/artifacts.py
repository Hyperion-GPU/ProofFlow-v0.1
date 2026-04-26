from fastapi import APIRouter, HTTPException, status

from proofflow.models.schemas import (
    ArtifactCreate,
    ArtifactResponse,
    CaseArtifactLinkCreate,
    CaseArtifactLinkResponse,
)
from proofflow.services import artifact_service
from proofflow.services.errors import NotFoundError

router = APIRouter(tags=["artifacts"])


@router.get("/artifacts", response_model=list[ArtifactResponse])
def list_artifacts() -> list[ArtifactResponse]:
    return artifact_service.list_artifacts()


@router.post(
    "/artifacts",
    response_model=ArtifactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_artifact(payload: ArtifactCreate) -> ArtifactResponse:
    return artifact_service.create_artifact(payload)


@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse)
def get_artifact(artifact_id: str) -> ArtifactResponse:
    try:
        return artifact_service.get_artifact(artifact_id)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post(
    "/cases/{case_id}/artifacts/{artifact_id}",
    response_model=CaseArtifactLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
def link_artifact_to_case(
    case_id: str,
    artifact_id: str,
    payload: CaseArtifactLinkCreate | None = None,
) -> CaseArtifactLinkResponse:
    link_payload = payload or CaseArtifactLinkCreate()
    try:
        return artifact_service.link_artifact_to_case(case_id, artifact_id, link_payload)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

