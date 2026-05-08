export interface CaseResponse {
  id: string;
  title: string;
  kind: string;
  status: string;
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
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface ActionPreview {
  from_path?: string;
  to_path?: string;
  content?: string;
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

export interface CasePacket {
  case_id: string;
  title: string;
  claims: CasePacketClaim[];
  evidence: CasePacketEvidence[];
  actions: CasePacketAction[];
}

export interface CasePacketClaim {
  claim_text: string;
  severity: string;
  evidence: string[];
}

export interface CasePacketEvidence {
  id: string;
  kind: string;
  content: string;
}

export interface CasePacketAction {
  id: string;
  title: string;
  status: string;
}
