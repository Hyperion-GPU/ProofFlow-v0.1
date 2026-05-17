import type { FormEvent } from "react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { apiGet, apiPost, formatApiError } from "../api/client";
import type { CasePacketResponse, IssueTriageResponse, ReportExportResponse } from "../types";

export function IssueTriage() {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [labelsText, setLabelsText] = useState("");
  const [result, setResult] = useState<IssueTriageResponse | null>(null);
  const [packet, setPacket] = useState<CasePacketResponse | null>(null);
  const [exportResult, setExportResult] = useState<ReportExportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [packetError, setPacketError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);

  async function triageIssue(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setResult(null);
    setPacket(null);
    setExportResult(null);
    setError(null);
    setPacketError(null);

    try {
      const response = await apiPost<IssueTriageResponse>("/issue-triage", {
        title: title.trim(),
        body,
        source_url: sourceUrl.trim() || null,
        labels: parseLabels(labelsText),
      });
      setResult(response);

      try {
        const packetResponse = await apiGet<CasePacketResponse>(
          `/cases/${response.case_id}/packet`,
        );
        setPacket(packetResponse);
      } catch (requestError: unknown) {
        setPacketError(
          `Case was created, but the detail summary could not be loaded: ${formatApiError(
            requestError,
          )}`,
        );
      }
    } catch (requestError: unknown) {
      setError(`Issue triage failed: ${formatApiError(requestError)}`);
    } finally {
      setLoading(false);
    }
  }

  async function exportPacket() {
    if (!result) return;
    setExporting(true);
    setError(null);
    try {
      const response = await apiPost<ReportExportResponse>(
        `/reports/cases/${result.case_id}/export`,
        { format: "markdown" },
      );
      setExportResult(response);
    } catch (requestError: unknown) {
      setError(`Proof Packet export failed: ${formatApiError(requestError)}`);
    } finally {
      setExporting(false);
    }
  }

  const claims = packet?.claims ?? [];

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Issue Triage</p>
          <h1>Issue to Proof Packet</h1>
        </div>
      </header>

      {error && <p className="error-text">{error}</p>}
      {packetError && <p className="error-text">{packetError}</p>}
      {exportResult && (
        <p className="success-text">
          Exported {exportResult.filename} at{" "}
          <span className="mono-cell">{exportResult.path}</span>
        </p>
      )}

      <form className="panel form-grid" onSubmit={triageIssue}>
        <div className="two-column">
          <label>
            Issue title
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Policy gate Execute button remains disabled"
            />
          </label>
          <label>
            Source URL
            <input
              value={sourceUrl}
              onChange={(event) => setSourceUrl(event.target.value)}
              placeholder="https://github.com/org/repo/issues/123"
            />
          </label>
        </div>
        <label>
          Labels
          <input
            value={labelsText}
            onChange={(event) => setLabelsText(event.target.value)}
            placeholder="bug, codex, usability"
          />
        </label>
        <label>
          Issue body
          <textarea
            value={body}
            onChange={(event) => setBody(event.target.value)}
            placeholder={"Steps to Reproduce\n1. ...\n\nExpected Behavior\n...\n\nEnvironment\n- OS: ..."}
          />
        </label>
        <p className="notice-text">
          This creates an issue_triage Case directly. The issue text becomes the primary
          Artifact, deterministic Claims record component and completeness signals, and
          the Case can be exported as a Proof Packet.
        </p>
        <button type="submit" disabled={!title.trim() || loading}>
          {loading ? "Triaging..." : "Create triage Case"}
        </button>
      </form>

      <section className="panel">
        <div className="section-heading">
          <h2>Triage result</h2>
          {result && (
            <div className="action-buttons">
              <Link className="secondary-action" to={`/cases/${result.case_id}`}>
                Open Case
              </Link>
              <button type="button" onClick={exportPacket} disabled={exporting}>
                {exporting ? "Exporting..." : "Export Packet"}
              </button>
            </div>
          )}
        </div>
        {!result && <p className="muted">No issue triaged yet.</p>}
        {result && (
          <>
            <div className="chip-row">
              <span className={`status-pill risk-${result.risk_level}`}>
                Risk {result.risk_level}
              </span>
              <span className="status-pill ok">Component {result.component}</span>
              <span className={triageSignalClass(result.has_reproduction_steps)}>
                Repro {signalText(result.has_reproduction_steps)}
              </span>
              <span className={triageSignalClass(result.has_expected_behavior)}>
                Expected {signalText(result.has_expected_behavior)}
              </span>
              <span className={triageSignalClass(result.has_environment_details)}>
                Env {signalText(result.has_environment_details)}
              </span>
            </div>
            <dl className="detail-list">
              <div>
                <dt>Case</dt>
                <dd className="mono-cell">
                  <Link to={`/cases/${result.case_id}`}>{result.case_id}</Link>
                </dd>
              </div>
              <div>
                <dt>Run</dt>
                <dd className="mono-cell">{result.run_id}</dd>
              </div>
              <div>
                <dt>Artifact</dt>
                <dd className="mono-cell">{result.artifact_id}</dd>
              </div>
              <div>
                <dt>Claims</dt>
                <dd>{result.claims_created}</dd>
              </div>
              <div>
                <dt>Evidence</dt>
                <dd>{result.evidence_created}</dd>
              </div>
            </dl>
            <h3>Suggested labels</h3>
            {result.suggested_labels.length === 0 ? (
              <p className="muted">No labels suggested.</p>
            ) : (
              <div className="chip-row">
                {result.suggested_labels.map((label) => (
                  <span className="status-pill" key={label}>
                    {label}
                  </span>
                ))}
              </div>
            )}
          </>
        )}
      </section>

      {result && (
        <section className="panel">
          <h2>Claims summary</h2>
          {!packet && !packetError && <p className="muted">Loading case details...</p>}
          {packet && claims.length === 0 && <p className="muted">No claims recorded.</p>}
          {claims.length > 0 && (
            <ul className="packet-list">
              {claims.map((claim) => (
                <li key={claim.id} className="packet-item">
                  <div className="section-heading compact">
                    <div>
                      <strong>{claim.claim_text}</strong>
                      <div className="muted">
                        {claim.claim_type} / {claim.status}
                      </div>
                    </div>
                    <span className={`status-pill risk-${claim.severity}`}>
                      {claim.severity}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </section>
  );
}

function parseLabels(value: string): string[] {
  const seen = new Set<string>();
  const labels: string[] = [];
  for (const rawLabel of value.split(",")) {
    const label = rawLabel.trim();
    const key = label.toLowerCase();
    if (!label || seen.has(key)) continue;
    labels.push(label);
    seen.add(key);
  }
  return labels;
}

function signalText(value: boolean): string {
  return value ? "present" : "missing";
}

function triageSignalClass(value: boolean): string {
  return `status-pill ${value ? "ok" : "warn"}`;
}
