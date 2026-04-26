export type JsonObject = Record<string, unknown>;

export type HealthResponse = {
  ok: boolean;
  service: string;
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
