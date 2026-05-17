from fastapi import APIRouter

from proofflow.models.schemas import IssueTriageRequest, IssueTriageResponse
from proofflow.services.issue_triage_service import triage_issue

router = APIRouter(tags=["issue-triage"])


@router.post("/issue-triage", response_model=IssueTriageResponse)
def triage_issue_text(payload: IssueTriageRequest) -> IssueTriageResponse:
    return triage_issue(payload)
