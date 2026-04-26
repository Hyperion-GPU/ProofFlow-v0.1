from fastapi import APIRouter, HTTPException, status

from proofflow.models.schemas import ActionCreate, ActionResponse
from proofflow.services import action_service
from proofflow.services.action_service import ActionError
from proofflow.services.errors import NotFoundError

router = APIRouter(tags=["actions"])


@router.get("/cases/{case_id}/actions", response_model=list[ActionResponse])
def list_case_actions(case_id: str) -> list[ActionResponse]:
    try:
        return action_service.list_case_actions(case_id)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error


@router.post("/actions", response_model=ActionResponse, status_code=status.HTTP_201_CREATED)
def create_action(payload: ActionCreate) -> ActionResponse:
    try:
        return action_service.create_action(payload)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ActionError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/actions/{action_id}/approve", response_model=ActionResponse)
def approve_action(action_id: str) -> ActionResponse:
    return _run_action_operation(action_id, action_service.approve_action)


@router.post("/actions/{action_id}/execute", response_model=ActionResponse)
def execute_action(action_id: str) -> ActionResponse:
    return _run_action_operation(action_id, action_service.execute_action)


@router.post("/actions/{action_id}/undo", response_model=ActionResponse)
def undo_action(action_id: str) -> ActionResponse:
    return _run_action_operation(action_id, action_service.undo_action)


@router.post("/actions/{action_id}/reject", response_model=ActionResponse)
def reject_action(action_id: str) -> ActionResponse:
    return _run_action_operation(action_id, action_service.reject_action)


def _run_action_operation(action_id: str, operation) -> ActionResponse:
    try:
        return operation(action_id)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ActionError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
