import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiGet, apiPost, formatApiError } from "../api/client";
import type {
  ActionResponse,
  CasePacketResponse,
  JsonObject,
  ReportExportResponse,
} from "../types";

type ActionOperation = "approve" | "execute" | "undo" | "reject";

const ACTION_LABELS: Record<ActionOperation, string> = {
  approve: "Approve",
  execute: "Execute",
  undo: "Undo",
  reject: "Reject",
};

export function CaseDetail() {
  const { caseId } = useParams<{ caseId: string }>();
  const [packet, setPacket] = useState<CasePacketResponse | null>(null);
  const [report, setReport] = useState<ReportExportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);

  useEffect(() => {
    if (!caseId) return;
    let active = true;
    setLoading(true);
    apiGet<CasePacketResponse>(`/cases/${caseId}/packet`)
      .then((response) => {
        if (!active) return;
        setPacket(response);
        setError(null);
      })
      .catch((requestError: unknown) => {
        if (!active) return;
        setError(formatApiError(requestError));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [caseId]);

  function refreshPacket() {
    if (!caseId) return Promise.resolve();
    return apiGet<CasePacketResponse>(`/cases/${caseId}/packet`).then((response) => {
      setPacket(response);
      setError(null);
    });
  }

  function exportReport() {
    if (!caseId) return;
    setExporting(true);
    apiPost<ReportExportResponse>(`/reports/cases/${caseId}/export`, { format: "markdown" })
      .then((response) => {
        setReport(response);
        setError(null);
        return refreshPacket();
      })
      .catch((requestError: unknown) => {
        setError(formatApiError(requestError));
      })
      .finally(() => setExporting(false));
  }

  function runAction(actionId: string, operation: ActionOperation) {
    setBusyAction(`${actionId}:${operation}`);
    apiPost<ActionResponse>(`/actions/${actionId}/${operation}`)
      .then(() => refreshPacket())
      .catch((requestError: unknown) => {
        setError(formatApiError(requestError));
      })
      .finally(() => setBusyAction(null));
  }

  const caseDetail = packet?.case;

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Case detail</p>
          <h1>{caseDetail?.title ?? "Loading case"}</h1>
          {packet && (
            <div className="chip-row">
              <span className="status-pill">{packet.case.kind}</span>
              <span className="status-pill">{packet.case.status}</span>
              <span className={`status-pill risk-${packet.risk_level}`}>
                Risk {packet.risk_level}
              </span>
            </div>
          )}
        </div>
        <Link className="secondary-action" to="/cases">
          Back to cases
        </Link>
      </header>

      {loading && <p className="muted">Loading case packet...</p>}
      {error && <p className="error-text">{error}</p>}

      {packet && (
        <>
          <section className="panel">
            <div className="section-heading">
              <h2>Summary</h2>
              <button type="button" onClick={exportReport} disabled={exporting}>
                {exporting ? "Exporting..." : "Export Proof Packet"}
              </button>
            </div>
            <p className="summary-text">{packet.case.summary ?? "No summary recorded."}</p>
            <dl className="detail-list">
              <div>
                <dt>Case ID</dt>
                <dd>{packet.case.id}</dd>
              </div>
              <div>
                <dt>Artifacts</dt>
                <dd>{packet.artifacts.length}</dd>
              </div>
              <div>
                <dt>Claims</dt>
                <dd>{packet.claims.length}</dd>
              </div>
              <div>
                <dt>Actions</dt>
                <dd>{packet.actions.length}</dd>
              </div>
              <div>
                <dt>Decisions</dt>
                <dd>{packet.case.decision_count}</dd>
              </div>
              <div>
                <dt>Updated</dt>
                <dd>{packet.case.updated_at}</dd>
              </div>
            </dl>
            {report && (
              <p className="success-text">
                Exported {report.filename} at {report.path}
              </p>
            )}
          </section>

          <section className="panel">
            <h2>Linked Artifacts</h2>
            {packet.artifacts.length === 0 ? (
              <p className="muted">No linked artifacts.</p>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Kind</th>
                      <th>Role</th>
                      <th>Path</th>
                      <th>Hash / Size</th>
                    </tr>
                  </thead>
                  <tbody>
                    {packet.artifacts.map((artifact) => (
                      <tr key={artifact.id}>
                        <td>
                          <strong>{artifact.name}</strong>
                          <div className="mono-cell">{artifact.id}</div>
                        </td>
                        <td>{artifact.kind}</td>
                        <td>{artifact.role}</td>
                        <td className="mono-cell">{artifact.path ?? artifact.uri}</td>
                        <td>
                          <span className="mono-cell">{artifact.sha256 ?? "not recorded"}</span>
                          <br />
                          <span className="muted">{formatSize(artifact.size_bytes)}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="panel">
            <h2>Claims & Evidence</h2>
            {packet.claims.length === 0 ? (
              <p className="muted">No claims recorded.</p>
            ) : (
              <ul className="packet-list">
                {packet.claims.map((claim) => (
                  <li key={claim.id} className="packet-item">
                    <div className="section-heading compact">
                      <div>
                        <strong>{claim.claim_text}</strong>
                        <div className="muted">
                          {claim.claim_type} · {claim.status}
                        </div>
                      </div>
                      <span className={`status-pill risk-${claim.severity}`}>
                        {claim.severity}
                      </span>
                    </div>
                    {claim.evidence.length === 0 ? (
                      <p className="muted">No evidence linked to this claim.</p>
                    ) : (
                      <ul className="evidence-list">
                        {claim.evidence.map((evidence) => (
                          <li key={evidence.id} className="evidence-item">
                            <div className="result-meta">
                              <span>
                                {evidence.evidence_type} ·{" "}
                                {evidence.artifact_name ?? evidence.artifact_id ?? "no artifact"}
                              </span>
                              <span>{evidence.source_ref ?? "no source ref"}</span>
                            </div>
                            <div className="mono-cell">
                              {evidence.artifact_path ?? "no artifact path recorded"}
                            </div>
                            <blockquote>{evidence.content || "No evidence content recorded."}</blockquote>
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>

          {packet.observations.length > 0 && (
            <section className="panel">
              <h2>Policy Gate Observations</h2>
              <p className="muted">
                Non-enforcing dry-run observations recorded at pre-execution.
              </p>
              <ul className="packet-list">
                {packet.observations.map((obs) => (
                  <li key={obs.id} className="packet-item">
                    <div className="section-heading compact">
                      <div>
                        <strong>{obs.action_type ?? "unknown"}</strong>
                        <div className="muted">
                          {obs.categories.join(", ")} · {obs.would_have_outcome}
                        </div>
                      </div>
                      <span className="status-pill">{obs.label}</span>
                    </div>
                    <dl className="detail-list compact-detail">
                      <div>
                        <dt>Outcome</dt>
                        <dd>{obs.would_have_outcome}</dd>
                      </div>
                      <div>
                        <dt>High risk</dt>
                        <dd>{obs.high_risk ? "yes" : "no"}</dd>
                      </div>
                      <div>
                        <dt>Enforcing</dt>
                        <dd>{obs.non_enforcing ? "no (observation only)" : "yes"}</dd>
                      </div>
                      <div>
                        <dt>Action</dt>
                        <dd className="mono-cell">{obs.action_id ?? "n/a"}</dd>
                      </div>
                      <div>
                        <dt>Observed</dt>
                        <dd>{obs.created_at}</dd>
                      </div>
                    </dl>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <section className="panel">
            <h2>Actions</h2>
            {packet.actions.length === 0 ? (
              <p className="muted">No actions recorded.</p>
            ) : (
              <ul className="packet-list">
                {packet.actions.map((action) => (
                  <li key={action.id} className="packet-item">
                    <div className="section-heading compact">
                      <div>
                        <strong>{action.title}</strong>
                        <div className="muted">
                          {action.kind} · {action.reason}
                        </div>
                      </div>
                      <span className={`status-pill${action.status === "pending_decision" ? " warn" : ""}`}>{action.status}</span>
                    </div>
                    <div className="json-grid">
                      <JsonBlock label="Preview" value={action.preview} />
                      <JsonBlock label="Result" value={action.result} />
                      <JsonBlock label="Undo" value={action.undo} />
                    </div>
                    {action.status === "pending_decision" && (
                      <PolicyGateBanner
                        action={action}
                        caseId={caseId!}
                        onDecisionCreated={() => refreshPacket()}
                        busy={busyAction !== null}
                      />
                    )}
                    <div className="action-buttons">
                      {(["approve", "execute", "undo", "reject"] as ActionOperation[]).map(
                        (operation) => (
                          <button
                            key={operation}
                            type="button"
                            disabled={
                              busyAction !== null ||
                              !canRunAction(action, operation) ||
                              busyAction === `${action.id}:${operation}`
                            }
                            onClick={() => runAction(action.id, operation)}
                          >
                            {busyAction === `${action.id}:${operation}`
                              ? "Working..."
                              : ACTION_LABELS[operation]}
                          </button>
                        ),
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <div className="two-column">
            <section className="panel">
              <h2>Decisions</h2>
              {packet.decisions.length === 0 ? (
                <p className="muted">No decisions recorded.</p>
              ) : (
                <ul className="packet-list">
                  {packet.decisions.map((decision) => (
                    <li key={decision.id} className="packet-item">
                      <div className="section-heading compact">
                        <strong>{decision.title}</strong>
                        <span className="status-pill">{decision.status}</span>
                      </div>
                      <p>{decision.rationale}</p>
                      <p className="muted">{decision.result}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="panel">
              <h2>Runs & Test Results</h2>
              {packet.runs.length === 0 ? (
                <p className="muted">No runs recorded.</p>
              ) : (
                <ul className="packet-list">
                  {packet.runs.map((run) => (
                    <li key={run.id} className="packet-item">
                      <div className="section-heading compact">
                        <strong>{run.run_type}</strong>
                        <span className="status-pill">{run.status}</span>
                      </div>
                      <dl className="detail-list compact-detail">
                        <div>
                          <dt>Started</dt>
                          <dd>{run.started_at}</dd>
                        </div>
                        <div>
                          <dt>Finished</dt>
                          <dd>{run.finished_at ?? "not recorded"}</dd>
                        </div>
                        <div>
                          <dt>Test Status</dt>
                          <dd>{metadataText(run.metadata, "test_status")}</dd>
                        </div>
                        <div>
                          <dt>Command</dt>
                          <dd>{metadataText(run.metadata, "test_command")}</dd>
                        </div>
                        <div>
                          <dt>Return Code</dt>
                          <dd>{metadataTextFallback(run.metadata, "test_returncode", "return_code")}</dd>
                        </div>
                      </dl>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </>
      )}
    </section>
  );
}

function JsonBlock({ label, value }: { label: string; value: unknown }) {
  return (
    <div>
      <strong>{label}</strong>
      <pre>{formatJson(value)}</pre>
    </div>
  );
}

function canRunAction(action: ActionResponse, operation: ActionOperation): boolean {
  if (operation === "approve") return action.status === "pending" || action.status === "previewed";
  if (operation === "execute") return action.status === "approved" || action.status === "pending_decision";
  if (operation === "undo") {
    return action.status === "executed" && action.kind !== "manual_check";
  }
  if (operation === "reject") {
    return (
      action.status === "pending" ||
      action.status === "previewed" ||
      action.status === "approved" ||
      action.status === "pending_decision"
    );
  }
  return false;
}

function formatJson(value: unknown): string {
  if (value === null || value === undefined || isEmptyObject(value)) {
    return "not recorded";
  }
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value, null, 2);
}

function isEmptyObject(value: unknown): boolean {
  return (
    typeof value === "object" &&
    value !== null &&
    !Array.isArray(value) &&
    Object.keys(value as Record<string, unknown>).length === 0
  );
}

function formatSize(sizeBytes: number | null): string {
  if (sizeBytes === null) return "size not recorded";
  if (sizeBytes < 1024) return `${sizeBytes} B`;
  const kib = sizeBytes / 1024;
  if (kib < 1024) return `${kib.toFixed(1)} KiB`;
  return `${(kib / 1024).toFixed(1)} MiB`;
}

function metadataText(metadata: JsonObject, key: string): string {
  const value = metadata[key];
  if (value === null || value === undefined) return "not recorded";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

function metadataTextFallback(metadata: JsonObject, primaryKey: string, fallbackKey: string): string {
  const primaryValue = metadata[primaryKey];
  if (primaryValue !== null && primaryValue !== undefined) {
    return metadataText(metadata, primaryKey);
  }
  return metadataText(metadata, fallbackKey);
}

function PolicyGateBanner({
  action,
  caseId,
  onDecisionCreated,
  busy,
}: {
  action: ActionResponse;
  caseId: string;
  onDecisionCreated: () => void;
  busy: boolean;
}) {
  const [creating, setCreating] = useState(false);
  const gate = action.metadata.policy_gate as Record<string, unknown> | undefined;
  if (!gate) return null;

  const categories = Array.isArray(gate.categories) ? (gate.categories as string[]).join(", ") : "";
  const reason = typeof gate.reason === "string" ? gate.reason : "";
  const pipelineId = gate.pipeline_id as string | undefined;
  const previewHash = gate.preview_hash as string | undefined;

  function createGateDecision() {
    setCreating(true);
    apiPost<unknown>(`/cases/${caseId}/decisions`, {
      title: `Approve gated action: ${action.title}`,
      status: "accepted",
      rationale: reason || "Owner approves high-risk action after review.",
      result: "proceed",
      metadata: {
        decision_kind: "policy_gate_owner_decision",
        action_id: action.id,
        policy_evaluation_id: pipelineId,
        preview_hash: previewHash,
      },
    })
      .then(() => onDecisionCreated())
      .catch(() => {})
      .finally(() => setCreating(false));
  }

  return (
    <div className="gate-banner">
      <strong>Policy gate — action paused</strong>
      {reason && <span>{reason}</span>}
      {categories && <span>Categories: {categories}</span>}
      <button type="button" onClick={createGateDecision} disabled={busy || creating}>
        {creating ? "Creating decision..." : "Approve & Resolve Gate"}
      </button>
    </div>
  );
}
