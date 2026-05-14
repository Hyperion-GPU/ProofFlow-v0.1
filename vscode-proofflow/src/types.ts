export interface CaseResponse {
  id: string;
  title: string;
  kind: string;
  status: string;
  summary?: string | null;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ActionResponse {
  id: string;
  case_id: string;
  title: string;
  status: string;
  kind: string;
  reason?: string;
  preview?: ActionPreview;
  metadata?: ActionMetadata;
  created_at: string;
}

export interface ActionPreview {
  from_path?: string;
  to_path?: string;
  dir_path?: string;
  content?: string;
}

export interface ActionMetadata {
  policy_gate?: PolicyGateMetadata;
  [key: string]: unknown;
}

export interface PolicyGateMetadata {
  pipeline_id?: unknown;
  preview_hash?: unknown;
  reason?: unknown;
  [key: string]: unknown;
}

export interface DecisionCreatePayload {
  title: string;
  status: "accepted";
  rationale: string;
  result: string;
  metadata: {
    decision_kind: "policy_gate_owner_decision";
    action_id: string;
    policy_evaluation_id: string;
    preview_hash: string;
    source: "vscode-proofflow";
  };
}

export interface DecisionResponse {
  id: string;
  case_id: string;
  title: string;
  status: string;
  rationale: string;
  result: string;
  created_at: string;
  updated_at: string;
}

export interface ReviewResponse {
  case_id: string;
  run_id: string;
  risk_level: string;
  changed_files: string[];
  claims_created: number;
  evidence_created: number;
}

export interface ScanResponse {
  case_id: string;
  files_seen: number;
  artifacts_created: number;
}

export interface HealthResponse {
  status: string;
  version: string;
}

export type RiskLevel = "low" | "info" | "medium" | "high";

export interface CasePacket {
  case: CaseResponse & { decision_count?: number };
  risk_level: RiskLevel;
  artifacts: CasePacketArtifact[];
  claims: CasePacketClaim[];
  actions: CasePacketAction[];
  decisions: DecisionResponse[];
  runs: CasePacketRun[];
  observations: unknown[];
}

export interface CasePacketArtifact {
  id: string;
  kind: string;
  role: string;
  name: string;
  uri: string;
  path?: string | null;
  mime_type?: string | null;
  sha256?: string | null;
  size_bytes?: number | null;
  created_at: string;
  updated_at: string;
}

export interface CasePacketClaim {
  id: string;
  run_id?: string | null;
  claim_text: string;
  claim_type: string;
  status: string;
  severity: RiskLevel;
  evidence: CasePacketEvidence[];
  created_at: string;
  updated_at: string;
}

export interface CasePacketEvidence {
  id: string;
  artifact_id?: string | null;
  claim_id?: string | null;
  evidence_type: string;
  content: string;
  source_ref?: string | null;
  artifact_name?: string | null;
  artifact_path?: string | null;
  source_location?: CasePacketSourceLocation | null;
  created_at: string;
}

export interface CasePacketSourceLocation {
  path: string;
  start_line: number;
  end_line: number;
  source: "source_ref" | "artifact_path";
}

export interface CasePacketAction {
  id: string;
  title: string;
  status: string;
}

export interface CasePacketRun {
  id: string;
  run_type: string;
  status: string;
  started_at: string;
  finished_at?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}
