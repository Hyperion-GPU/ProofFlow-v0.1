from fastapi import APIRouter, HTTPException, status

from proofflow.models.schemas import ReportExportRequest, ReportExportResponse
from proofflow.services.errors import NotFoundError
from proofflow.services.report_service import ReportExportError, export_case_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/cases/{case_id}/export", response_model=ReportExportResponse)
def export_case_proof_packet(
    case_id: str,
    payload: ReportExportRequest,
) -> ReportExportResponse:
    try:
        return export_case_report(case_id, payload)
    except NotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ReportExportError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
