/**
 * TypeScript shapes for ProofFlow MCP tool responses.
 *
 * The MCP server returns each tool result as a single TextContent block whose
 * text is the JSON body of the underlying ProofFlow REST endpoint (see
 * mcp-server/src/proofflow_mcp/server.py). Types here mirror what the backend
 * returns so the rest of the extension can stay typed.
 */

export type ProofFlowMcpState =
  | "idle"
  | "starting"
  | "ready"
  | "restarting"
  | "failed";

export interface McpHealth {
  status: string;
  version: string;
}

export interface McpCase {
  id: string;
  title: string;
  kind: string;
  status: string;
  summary?: string | null;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface McpAction {
  id: string;
  case_id: string;
  title: string;
  status: string;
  kind: string;
  reason?: string;
  preview?: {
    from_path?: string;
    to_path?: string;
    dir_path?: string;
    content?: string;
  };
  metadata?: {
    policy_gate?: {
      pipeline_id?: unknown;
      preview_hash?: unknown;
      reason?: unknown;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
  created_at: string;
}

export interface McpReviewResult {
  case_id: string;
  run_id: string;
  risk_level: string;
  changed_files: string[];
  claims_created: number;
  evidence_created: number;
}

export interface McpScanResult {
  case_id: string;
  files_seen: number;
  artifacts_created: number;
}

export interface McpDecisionPayload {
  title: string;
  status: "accepted" | "rejected";
  rationale: string;
  result: string;
  metadata?: Record<string, unknown>;
}

export interface McpDecision {
  id: string;
  case_id: string;
  title: string;
  status: string;
  rationale: string;
  result: string;
  created_at: string;
  updated_at: string;
}

export type McpRiskLevel = "low" | "info" | "medium" | "high";

export interface McpSourceLocation {
  path: string;
  start_line: number;
  end_line: number;
  source: "source_ref" | "artifact_path";
}

export interface McpEvidence {
  id: string;
  artifact_id?: string | null;
  claim_id?: string | null;
  evidence_type: string;
  content: string;
  source_ref?: string | null;
  artifact_name?: string | null;
  artifact_path?: string | null;
  source_location?: McpSourceLocation | null;
  created_at: string;
}

export interface McpClaim {
  id: string;
  run_id?: string | null;
  claim_text: string;
  claim_type: string;
  status: string;
  severity: McpRiskLevel;
  evidence: McpEvidence[];
  created_at: string;
  updated_at: string;
}

export interface McpArtifact {
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

export interface McpRun {
  id: string;
  run_type: string;
  status: string;
  started_at: string;
  finished_at?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface McpCasePacket {
  case: McpCase & { decision_count?: number };
  risk_level: McpRiskLevel;
  artifacts: McpArtifact[];
  claims: McpClaim[];
  actions: McpAction[];
  decisions: McpDecision[];
  runs: McpRun[];
  observations: unknown[];
}

export interface McpEvaluationResult {
  case_id: string;
  run_id: string;
  status: string;
  passed: string[];
  failed: string[];
  warnings: string[];
  missing_evidence: string[];
  scope_violations: string[];
  risk_hints: McpRiskHint[];
  metadata?: Record<string, unknown>;
}

export interface McpRiskHint {
  hint_code: string;
  severity: McpRiskLevel;
  message: string;
  evidence_ids?: string[];
}

export interface McpExportResult {
  case_id: string;
  format: "markdown";
  content: string;
}

export interface McpSearchHit {
  case_id: string;
  artifact_id?: string;
  evidence_id?: string;
  snippet: string;
  score: number;
}

export interface McpSearchResult {
  query: string;
  hits: McpSearchHit[];
}
