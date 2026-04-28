export type JsonObject = Record<string, unknown>;

export type HealthResponse = {
  ok: boolean;
  service: string;
  version: string;
  release_stage: string;
  release_name: string;
};

export type CaseResponse = {
  id: string;
  title: string;
  kind: string;
  status: string;
  summary: string | null;
  metadata: JsonObject;
  created_at: string;
  updated_at: string;
};

export type CaseDetailResponse = CaseResponse & {
  decision_count: number;
};

export type ArtifactResponse = {
  id: string;
  kind: string;
  uri: string;
  name: string;
  mime_type: string | null;
  sha256: string | null;
  size_bytes: number | null;
  metadata: JsonObject;
  created_at: string;
  updated_at: string;
};

export type SearchResult = {
  artifact_id: string;
  chunk_id: string;
  name: string;
  path: string | null;
  snippet: string;
  start_line: number;
  end_line: number;
  score: number;
};

export type SearchResponse = {
  query: string;
  results: SearchResult[];
};

export type LocalProofScanSummary = {
  case_id: string;
  files_seen: number;
  artifacts_created: number;
  artifacts_updated: number;
  text_chunks_created: number;
  skipped: number;
  skipped_items: Array<{
    path: string;
    reason: string;
    indexed: boolean;
  }>;
};

export type ActionResponse = {
  id: string;
  case_id: string;
  kind: string;
  status: string;
  title: string;
  reason: string;
  preview: JsonObject;
  result: JsonObject | null;
  undo: JsonObject | null;
  metadata: JsonObject;
  created_at: string;
  updated_at: string;
};

export type LocalProofSuggestActionsSummary = {
  case_id: string;
  target_root: string;
  actions_created: number;
  skipped: number;
  skipped_items: Array<{
    artifact_id: string;
    path: string | null;
    reason: string;
  }>;
  actions: ActionResponse[];
};

export type AgentGuardReviewResponse = {
  case_id: string;
  run_id: string;
  risk_level: "low" | "info" | "medium" | "high";
  changed_files: string[];
  claims_created: number;
  evidence_created: number;
  artifacts: Array<{
    id: string;
    kind: string;
    name: string;
  }>;
};

export type DecisionStatus = "proposed" | "accepted" | "rejected" | "superseded";

export type DecisionResponse = {
  id: string;
  case_id: string;
  title: string;
  status: DecisionStatus;
  rationale: string;
  result: string;
  created_at: string;
  updated_at: string;
};

export type ReportExportResponse = {
  case_id: string;
  artifact_id: string;
  format: "markdown";
  path: string;
  filename: string;
  created_at: string;
  content: string;
};

export type RiskLevel = "low" | "info" | "medium" | "high";

export type CasePacketArtifact = {
  id: string;
  kind: string;
  role: string;
  name: string;
  uri: string;
  path: string | null;
  mime_type: string | null;
  sha256: string | null;
  size_bytes: number | null;
  created_at: string;
  updated_at: string;
};

export type CasePacketEvidence = {
  id: string;
  artifact_id: string | null;
  claim_id: string | null;
  evidence_type: string;
  content: string;
  source_ref: string | null;
  artifact_name: string | null;
  artifact_path: string | null;
  created_at: string;
};

export type CasePacketClaim = {
  id: string;
  run_id: string | null;
  claim_text: string;
  claim_type: string;
  status: string;
  severity: RiskLevel;
  evidence: CasePacketEvidence[];
  created_at: string;
  updated_at: string;
};

export type CasePacketRun = {
  id: string;
  run_type: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  metadata: JsonObject;
  created_at: string;
  updated_at: string;
};

export type CasePacketResponse = {
  case: CaseDetailResponse;
  risk_level: RiskLevel;
  artifacts: CasePacketArtifact[];
  claims: CasePacketClaim[];
  actions: ActionResponse[];
  decisions: DecisionResponse[];
  runs: CasePacketRun[];
};

export type BackupSource = {
  db_path: string;
  data_dir: string;
  proof_packets_dir: string;
};

export type PlannedBackupFile = {
  role: string;
  relative_path: string;
  size_bytes: number;
  source_path: string;
};

export type BackupPreviewRequest = {
  backup_root: string;
  include_data_dir?: boolean;
  include_proof_packets?: boolean;
};

export type BackupPreviewResponse = {
  source: BackupSource;
  planned_files: PlannedBackupFile[];
  warnings: string[];
  would_create_case: boolean;
};

export type BackupCreateRequest = {
  backup_root: string;
  label?: string | null;
};

export type BackupCreateResponse = {
  backup_id: string;
  case_id: string;
  archive_path: string;
  manifest_path: string;
  manifest_sha256: string;
  archive_sha256: string;
  warnings: string[];
};

export type BackupListItem = {
  backup_id: string;
  created_at: string;
  status: string;
  verified_at: string | null;
  archive_path: string;
};

export type BackupListResponse = {
  backups: BackupListItem[];
};

export type BackupManifestSummary = {
  manifest_version: string | null;
  app_version: string | null;
  schema_version: string | null;
};

export type BackupVerificationSummary = {
  status: string;
  verified_at: string | null;
  errors: string[];
};

export type BackupDetailResponse = {
  backup_id: string;
  case_id: string | null;
  manifest: BackupManifestSummary | null;
  archive_path: string;
  verification: BackupVerificationSummary;
  warnings: string[];
};

export type BackupHashMismatch = {
  relative_path: string;
  expected_sha256: string | null;
  actual_sha256: string | null;
};

export type BackupVerifyResponse = {
  backup_id: string;
  case_id: string | null;
  status: string;
  checked_files: number;
  hash_mismatches: BackupHashMismatch[];
  missing_files: string[];
  warnings: string[];
};

export type RestoreTarget = {
  db_path: string;
  data_dir: string;
};

export type RestoreRisk = {
  code: string;
  message: string;
  blocking: boolean;
};

export type RestorePlannedWrite = {
  archive_relative_path: string;
  target_path: string;
  role: string;
  action: "create" | "overwrite" | "skip";
  size_bytes: number;
  sha256: string;
  would_overwrite: boolean;
};

export type RestorePreviewRequest = {
  backup_id: string;
  target_db_path: string;
  target_data_dir: string;
};

export type RestorePreviewResponse = {
  restore_preview_id: string;
  backup_id: string;
  case_id: string | null;
  verified: boolean;
  target: RestoreTarget;
  planned_writes: RestorePlannedWrite[];
  plan_hash: string;
  schema_risks: RestoreRisk[];
  version_risks: RestoreRisk[];
  warnings: string[];
};

export type RestoreToNewLocationRequest = RestorePreviewRequest & {
  accepted_preview_id: string;
};

export type RestoreToNewLocationResponse = {
  backup_id: string;
  restore_preview_id: string;
  case_id: string | null;
  target: RestoreTarget;
  restored_files: number;
  status: "restored_to_new_location";
  warnings: string[];
};
