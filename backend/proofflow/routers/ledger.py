from fastapi import APIRouter, HTTPException, status

from proofflow.models.schemas import (
    LedgerAlgorithmDecisionCreateRequest,
    LedgerAlgorithmDecisionResponse,
    LedgerClaimCreateRequest,
    LedgerClaimCreateResponse,
    LedgerCostBudgetCreateRequest,
    LedgerCostBudgetResponse,
    LedgerEvaluationResponse,
    LedgerEventCreateRequest,
    LedgerEventResponse,
    LedgerEvidenceCreateRequest,
    LedgerEvidenceCreateResponse,
    LedgerFinishRequest,
    LedgerFinishResponse,
    WorkContractStartRequest,
    WorkContractStartResponse,
    WorkSnapshotRequest,
    WorkSnapshotResponse,
)
from proofflow.services.errors import NotFoundError
from proofflow.services.git_service import GitServiceError
from proofflow.services.ledger_service import (
    LedgerServiceError,
    capture_snapshot,
    evaluate_contract,
    finish_work_ledger,
    record_algorithm_decision,
    record_claim,
    record_cost_budget,
    record_event,
    record_evidence,
    start_work_contract,
)

router = APIRouter(prefix="/ledger", tags=["ledger"])


@router.post("/start", response_model=WorkContractStartResponse)
def start_ledger(payload: WorkContractStartRequest) -> WorkContractStartResponse:
    return start_work_contract(payload)


@router.post("/cases/{case_id}/events", response_model=LedgerEventResponse)
def create_ledger_event(
    case_id: str,
    payload: LedgerEventCreateRequest,
) -> LedgerEventResponse:
    try:
        return record_event(case_id, payload)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except LedgerServiceError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post(
    "/cases/{case_id}/algorithm-decisions",
    response_model=LedgerAlgorithmDecisionResponse,
)
def create_ledger_algorithm_decision(
    case_id: str,
    payload: LedgerAlgorithmDecisionCreateRequest,
) -> LedgerAlgorithmDecisionResponse:
    try:
        return record_algorithm_decision(case_id, payload)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except LedgerServiceError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/cases/{case_id}/cost-budgets", response_model=LedgerCostBudgetResponse)
def create_ledger_cost_budget(
    case_id: str,
    payload: LedgerCostBudgetCreateRequest,
) -> LedgerCostBudgetResponse:
    try:
        return record_cost_budget(case_id, payload)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except LedgerServiceError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/cases/{case_id}/finish", response_model=LedgerFinishResponse)
def finish_ledger(
    case_id: str,
    payload: LedgerFinishRequest,
) -> LedgerFinishResponse:
    try:
        return finish_work_ledger(case_id, payload)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except LedgerServiceError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/cases/{case_id}/snapshots", response_model=WorkSnapshotResponse)
def create_ledger_snapshot(
    case_id: str,
    payload: WorkSnapshotRequest,
) -> WorkSnapshotResponse:
    try:
        return capture_snapshot(case_id, payload)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except (GitServiceError, LedgerServiceError) as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/cases/{case_id}/evaluate", response_model=LedgerEvaluationResponse)
def evaluate_ledger(case_id: str) -> LedgerEvaluationResponse:
    try:
        return evaluate_contract(case_id)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except LedgerServiceError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/cases/{case_id}/evidence", response_model=LedgerEvidenceCreateResponse)
def create_ledger_evidence(
    case_id: str,
    payload: LedgerEvidenceCreateRequest,
) -> LedgerEvidenceCreateResponse:
    try:
        return record_evidence(case_id, payload)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except LedgerServiceError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error


@router.post("/cases/{case_id}/claims", response_model=LedgerClaimCreateResponse)
def create_ledger_claim(
    case_id: str,
    payload: LedgerClaimCreateRequest,
) -> LedgerClaimCreateResponse:
    try:
        return record_claim(case_id, payload)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except LedgerServiceError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
