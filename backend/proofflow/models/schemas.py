from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CaseKind = Literal[
    "local_proof",
    "agent_guard",
    "file_cleanup",
    "code_review",
    "agent_work_ledger",
    "managed_backup",
    "issue_triage",
]
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
    "issue",
]
CaseArtifactRole = Literal["primary", "supporting", "reference"]
ActionKind = Literal["move_file", "rename_file", "manual_check", "mkdir_dir"]
ActionStatus = Literal["pending", "previewed", "approved", "executed", "undone", "rejected", "pending_decision"]
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


class DirectoryActionPreview(StrictRequest):
    dir_path: str = Field(min_length=1)


class ActionCreate(StrictRequest):
    case_id: str = Field(min_length=1)
    kind: ActionKind
    title: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    preview: FileActionPreview | DirectoryActionPreview | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_preview_for_previewable_actions(self) -> "ActionCreate":
        if self.kind in {"move_file", "rename_file"} and not isinstance(
            self.preview,
            FileActionPreview,
        ):
            raise ValueError("move_file and rename_file actions require file preview")
        if self.kind == "mkdir_dir" and not isinstance(
            self.preview,
            DirectoryActionPreview,
        ):
            raise ValueError("mkdir_dir actions require directory preview")
        if self.kind == "manual_check" and self.preview is not None:
            raise ValueError("manual_check actions do not accept preview")
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


class WorkContractStartRequest(StrictRequest):
    objective: str = Field(min_length=1)
    repo_path: str = Field(min_length=1)
    allowed_scope: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    required_tests: list[str] = Field(default_factory=list)
    done_criteria: list[str] = Field(default_factory=list)
    evidence_requirements: list[str] = Field(default_factory=list)


class WorkContractStartResponse(BaseModel):
    case_id: str
    status: str
    case: CaseResponse


class LedgerEventCreateRequest(StrictRequest):
    event_type: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class LedgerEventResponse(BaseModel):
    case_id: str
    artifact_id: str
    sequence: int
    event_type: str
    name: str
    created_at: str


class LedgerFinishRequest(StrictRequest):
    summary: str | None = Field(default=None, min_length=1)


class LedgerFinishResponse(BaseModel):
    case_id: str
    status: str
    finished_at: str
    metadata: dict[str, Any]


SnapshotPhase = Literal["start", "checkpoint", "final"]


class WorkSnapshotRequest(StrictRequest):
    repo_path: str = Field(min_length=1)
    phase: SnapshotPhase
    base_ref: str = Field(default="HEAD", min_length=1)
    include_untracked: bool = True


class WorkSnapshotResponse(BaseModel):
    case_id: str
    artifact_id: str
    phase: SnapshotPhase
    head_sha: str
    base_ref: str
    changed_files: list[str]
    diff_sha256: str


class LedgerEvidenceCreateRequest(StrictRequest):
    evidence_type: str = Field(min_length=1)
    content: str = Field(min_length=1)
    source_ref: str | None = Field(default=None, min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LedgerEvidenceCreateResponse(BaseModel):
    case_id: str
    artifact_id: str
    evidence_id: str
    evidence_type: str
    created_at: str


class LedgerClaimCreateRequest(StrictRequest):
    claim_text: str = Field(min_length=1)
    severity: RiskLevel = "info"
    evidence_ids: list[str] = Field(min_length=1)


class LedgerClaimCreateResponse(BaseModel):
    case_id: str
    claim_id: str
    evidence_ids: list[str]
    created_at: str


class LedgerEvaluationResponse(BaseModel):
    case_id: str
    run_id: str
    status: str
    passed: list[str]
    failed: list[str]
    warnings: list[str]
    missing_evidence: list[str]
    scope_violations: list[str]


class IssueTriageRequest(StrictRequest):
    title: str = Field(min_length=1)
    body: str = ""
    source_url: str | None = Field(default=None, min_length=1)
    labels: list[str] = Field(default_factory=list)


class IssueTriageResponse(BaseModel):
    case_id: str
    run_id: str
    risk_level: RiskLevel
    artifact_id: str
    component: str
    suggested_labels: list[str]
    has_reproduction_steps: bool
    has_expected_behavior: bool
    has_environment_details: bool
    claims_created: int
    evidence_created: int


class DecisionCreate(StrictRequest):
    title: str = Field(min_length=1)
    status: DecisionStatus
    rationale: str = Field(min_length=1)
    result: str = Field(min_length=1)
    metadata: dict[str, Any] | None = None


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


class CasePacketSourceLocation(BaseModel):
    path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    source: Literal["source_ref", "artifact_path"]


class CasePacketEvidence(BaseModel):
    id: str
    artifact_id: str | None
    claim_id: str | None
    evidence_type: str
    content: str
    source_ref: str | None
    artifact_name: str | None
    artifact_path: str | None
    source_location: CasePacketSourceLocation | None = None
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


class PolicyGateObservationSummary(BaseModel):
    id: str
    action_id: str | None
    action_type: str | None
    high_risk: bool
    non_enforcing: bool
    would_have_outcome: str
    categories: list[str]
    label: str
    created_at: str


class CasePacketResponse(BaseModel):
    case: CaseDetailResponse
    risk_level: RiskLevel
    artifacts: list[CasePacketArtifact]
    claims: list[CasePacketClaim]
    actions: list[ActionResponse]
    decisions: list[DecisionResponse]
    runs: list[CasePacketRun]
    observations: list[PolicyGateObservationSummary]


class BackupSource(BaseModel):
    db_path: str
    data_dir: str
    proof_packets_dir: str


class PlannedBackupFile(BaseModel):
    role: str
    relative_path: str
    size_bytes: int = Field(ge=0)
    source_path: str


class BackupPreviewRequest(StrictRequest):
    backup_root: str = Field(min_length=1)
    include_data_dir: bool = True
    include_proof_packets: bool = True


class BackupPreviewResponse(BaseModel):
    source: BackupSource
    planned_files: list[PlannedBackupFile]
    warnings: list[str]
    would_create_case: bool


class BackupCreateRequest(StrictRequest):
    backup_root: str = Field(min_length=1)
    label: str | None = Field(default=None, min_length=1)


class BackupCreateResponse(BaseModel):
    backup_id: str
    case_id: str
    archive_path: str
    manifest_path: str
    manifest_sha256: str
    archive_sha256: str
    warnings: list[str]


class BackupListItem(BaseModel):
    backup_id: str
    created_at: str
    status: str
    verified_at: str | None
    archive_path: str


class BackupListResponse(BaseModel):
    backups: list[BackupListItem]


class BackupManifestSummary(BaseModel):
    manifest_version: str | None = None
    app_version: str | None = None
    schema_version: str | None = None


class BackupVerificationSummary(BaseModel):
    status: str
    verified_at: str | None
    errors: list[str] = Field(default_factory=list)


class BackupDetailResponse(BaseModel):
    backup_id: str
    case_id: str | None
    manifest: BackupManifestSummary | None
    archive_path: str
    verification: BackupVerificationSummary
    warnings: list[str]


class BackupVerifyRequest(StrictRequest):
    recompute_archive_hash: bool = True
    recompute_file_hashes: bool = True


class BackupHashMismatch(BaseModel):
    relative_path: str
    expected_sha256: str | None
    actual_sha256: str | None


class BackupVerifyResponse(BaseModel):
    backup_id: str
    case_id: str | None
    status: str
    checked_files: int
    hash_mismatches: list[BackupHashMismatch]
    missing_files: list[str]
    warnings: list[str]


class RestoreTarget(BaseModel):
    db_path: str
    data_dir: str


class RestoreRisk(BaseModel):
    code: str
    message: str
    blocking: bool = False


class RestoreWarning(BaseModel):
    message: str


class RestorePlannedWrite(BaseModel):
    archive_relative_path: str
    target_path: str
    role: str
    action: Literal["create", "overwrite", "skip"]
    size_bytes: int = Field(ge=0)
    sha256: str
    would_overwrite: bool


class RestorePreviewRequest(StrictRequest):
    backup_id: str = Field(min_length=1)
    target_db_path: str = Field(min_length=1)
    target_data_dir: str = Field(min_length=1)


class RestorePreviewResponse(BaseModel):
    restore_preview_id: str
    backup_id: str
    case_id: str | None
    verified: bool
    target: RestoreTarget
    planned_writes: list[RestorePlannedWrite]
    plan_hash: str
    schema_risks: list[RestoreRisk]
    version_risks: list[RestoreRisk]
    warnings: list[str]


class RestoreToNewLocationRequest(StrictRequest):
    backup_id: str = Field(min_length=1)
    target_db_path: str = Field(min_length=1)
    target_data_dir: str = Field(min_length=1)
    accepted_preview_id: str = Field(min_length=1)


class RestoreToNewLocationResponse(BaseModel):
    backup_id: str
    restore_preview_id: str
    case_id: str | None
    target: RestoreTarget
    restored_files: int
    status: Literal["restored_to_new_location"]
    warnings: list[str]
