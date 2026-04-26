from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CaseKind = Literal["local_proof", "agent_guard", "file_cleanup", "code_review"]
CaseStatus = Literal["open", "active", "closed", "archived"]
ArtifactKind = Literal[
    "file",
    "text",
    "code",
    "image",
    "log",
    "pdf",
    "diff",
    "git_diff",
    "note",
    "command_output",
    "test_result",
    "test_output",
    "proof_packet",
    "screenshot",
]
CaseArtifactRole = Literal["primary", "supporting", "reference"]
ActionKind = Literal["move_file", "rename_file", "manual_check"]
ActionStatus = Literal["pending", "previewed", "approved", "executed", "undone", "rejected"]
DecisionStatus = Literal["proposed", "accepted", "rejected", "superseded"]


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CaseCreate(StrictRequest):
    title: str = Field(min_length=1)
    kind: CaseKind
    summary: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    status: CaseStatus = "open"


class CaseUpdate(StrictRequest):
    title: str | None = Field(default=None, min_length=1)
    status: CaseStatus | None = None
    summary: str | None = None
    metadata: dict[str, Any] | None = None

    @model_validator(mode="after")
    def reject_null_metadata(self) -> "CaseUpdate":
        if "metadata" in self.model_fields_set and self.metadata is None:
            raise ValueError("metadata must be a JSON object")
        return self


class CaseResponse(BaseModel):
    id: str
    title: str
    kind: CaseKind
    status: CaseStatus
    summary: str | None
    metadata: dict[str, Any]
    created_at: str
    updated_at: str


class CaseDetailResponse(CaseResponse):
    decision_count: int


class ArtifactCreate(StrictRequest):
    kind: ArtifactKind
    uri: str = Field(min_length=1)
    name: str = Field(min_length=1)
    mime_type: str | None = None
    sha256: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactResponse(BaseModel):
    id: str
    kind: ArtifactKind
    uri: str
    name: str
    mime_type: str | None
    sha256: str | None
    size_bytes: int | None
    metadata: dict[str, Any]
    created_at: str
    updated_at: str


class CaseArtifactLinkCreate(StrictRequest):
    role: CaseArtifactRole = "supporting"


class CaseArtifactLinkResponse(BaseModel):
    case_id: str
    artifact_id: str
    role: CaseArtifactRole
    created_at: str
    updated_at: str


class LocalProofScanRequest(StrictRequest):
    folder_path: str = Field(min_length=1)
    recursive: bool = True
    max_files: int = Field(default=500, ge=1)


class LocalProofSkippedItem(BaseModel):
    path: str
    reason: str
    indexed: bool


class LocalProofScanSummary(BaseModel):
    case_id: str
    files_seen: int
    artifacts_created: int
    artifacts_updated: int
    text_chunks_created: int
    skipped: int
    skipped_items: list[LocalProofSkippedItem]


class LocalProofSuggestActionsRequest(StrictRequest):
    case_id: str = Field(min_length=1)
    target_root: str = Field(min_length=1)


class LocalProofSuggestSkippedItem(BaseModel):
    artifact_id: str
    path: str | None
    reason: str


class SearchResult(BaseModel):
    artifact_id: str
    chunk_id: str
    name: str
    path: str | None
    snippet: str
    start_line: int
    end_line: int
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


class FileActionPreview(StrictRequest):
    from_path: str = Field(min_length=1)
    to_path: str = Field(min_length=1)


class ActionCreate(StrictRequest):
    case_id: str = Field(min_length=1)
    kind: ActionKind
    title: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    preview: FileActionPreview | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_preview_for_file_actions(self) -> "ActionCreate":
        if self.kind in {"move_file", "rename_file"} and self.preview is None:
            raise ValueError("move_file and rename_file actions require preview")
        return self


class ActionResponse(BaseModel):
    id: str
    case_id: str
    kind: ActionKind
    status: ActionStatus
    title: str
    reason: str
    preview: dict[str, Any]
    result: dict[str, Any] | None
    undo: dict[str, Any] | None
    metadata: dict[str, Any]
    created_at: str
    updated_at: str


class LocalProofSuggestActionsSummary(BaseModel):
    case_id: str
    target_root: str
    actions_created: int
    skipped: int
    skipped_items: list[LocalProofSuggestSkippedItem]
    actions: list[ActionResponse]


RiskLevel = Literal["low", "info", "medium", "high"]


class AgentGuardReviewRequest(StrictRequest):
    repo_path: str = Field(min_length=1)
    base_ref: str = Field(default="HEAD", min_length=1)
    include_untracked: bool = True
    test_command: str | None = None


class AgentGuardArtifactRef(BaseModel):
    id: str
    kind: ArtifactKind
    name: str


class AgentGuardReviewResponse(BaseModel):
    case_id: str
    run_id: str
    risk_level: RiskLevel
    changed_files: list[str]
    claims_created: int
    evidence_created: int
    artifacts: list[AgentGuardArtifactRef]


class DecisionCreate(StrictRequest):
    title: str = Field(min_length=1)
    status: DecisionStatus
    rationale: str = Field(min_length=1)
    result: str = Field(min_length=1)


class DecisionUpdate(StrictRequest):
    title: str | None = Field(default=None, min_length=1)
    status: DecisionStatus | None = None
    rationale: str | None = Field(default=None, min_length=1)
    result: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def reject_null_fields(self) -> "DecisionUpdate":
        for field_name in ("title", "status", "rationale", "result"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} must not be null")
        return self


class DecisionResponse(BaseModel):
    id: str
    case_id: str
    title: str
    status: DecisionStatus
    rationale: str
    result: str
    created_at: str
    updated_at: str


class ReportExportRequest(StrictRequest):
    format: Literal["markdown"] = "markdown"


class ReportExportResponse(BaseModel):
    case_id: str
    artifact_id: str
    format: Literal["markdown"]
    path: str
    filename: str
    created_at: str
    content: str


class CasePacketArtifact(BaseModel):
    id: str
    kind: ArtifactKind
    role: CaseArtifactRole
    name: str
    uri: str
    path: str | None
    mime_type: str | None
    sha256: str | None
    size_bytes: int | None
    created_at: str
    updated_at: str


class CasePacketEvidence(BaseModel):
    id: str
    artifact_id: str | None
    claim_id: str | None
    evidence_type: str
    content: str
    source_ref: str | None
    artifact_name: str | None
    artifact_path: str | None
    created_at: str


class CasePacketClaim(BaseModel):
    id: str
    run_id: str | None
    claim_text: str
    claim_type: str
    status: str
    severity: RiskLevel
    evidence: list[CasePacketEvidence]
    created_at: str
    updated_at: str


class CasePacketRun(BaseModel):
    id: str
    run_type: str
    status: str
    started_at: str
    finished_at: str | None
    metadata: dict[str, Any]
    created_at: str
    updated_at: str


class CasePacketResponse(BaseModel):
    case: CaseDetailResponse
    risk_level: RiskLevel
    artifacts: list[CasePacketArtifact]
    claims: list[CasePacketClaim]
    actions: list[ActionResponse]
    decisions: list[DecisionResponse]
    runs: list[CasePacketRun]
