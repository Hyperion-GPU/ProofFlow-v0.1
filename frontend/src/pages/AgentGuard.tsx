import type { FormEvent } from "react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { apiGet, apiPost, formatApiError } from "../api/client";
import type { AgentGuardReviewResponse, CasePacketResponse, JsonObject } from "../types";

export function AgentGuard() {
  const [repoPath, setRepoPath] = useState("");
  const [baseRef, setBaseRef] = useState("HEAD");
  const [includeUntracked, setIncludeUntracked] = useState(true);
  const [testCommand, setTestCommand] = useState("");
  const [result, setResult] = useState<AgentGuardReviewResponse | null>(null);
  const [packet, setPacket] = useState<CasePacketResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [packetError, setPacketError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function runReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setResult(null);
    setPacket(null);
    setError(null);
    setPacketError(null);

    try {
      const response = await apiPost<AgentGuardReviewResponse>("/agentguard/review", {
        repo_path: repoPath,
        base_ref: baseRef,
        include_untracked: includeUntracked,
        test_command: testCommand.trim() ? testCommand : null,
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
      setError(reviewErrorText(requestError));
    } finally {
      setLoading(false);
    }
  }

  const run = packet?.runs.find((item) => item.id === result?.run_id) ?? packet?.runs[0];
  const testStatus = metadataText(run?.metadata, "test_status");
  const testCommandText = metadataText(run?.metadata, "test_command");
  const testReturnCode = metadataText(run?.metadata, "test_returncode");
  const claims = packet?.claims ?? [];
  const testFailed = testStatus === "failed" || testStatus === "timeout";

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">AgentGuard</p>
          <h1>Code review workflow</h1>
        </div>
      </header>

      {error && <p className="error-text">{error}</p>}
      {packetError && <p className="error-text">{packetError}</p>}

      <form className="panel form-grid" onSubmit={runReview}>
        <label>
          Repo path
          <input
            value={repoPath}
            placeholder="D:\\my-repo"
            onChange={(event) => setRepoPath(event.target.value)}
          />
        </label>
        <label>
          Base ref
          <input value={baseRef} onChange={(event) => setBaseRef(event.target.value)} />
        </label>
        <label>
          Test command
          <input
            value={testCommand}
            onChange={(event) => setTestCommand(event.target.value)}
            placeholder="Leave empty to skip, or use: python -m pytest"
          />
        </label>
        <label className="inline-field">
          <input
            type="checkbox"
            checked={includeUntracked}
            onChange={(event) => setIncludeUntracked(event.target.checked)}
          />
          Include untracked files
        </label>
        <p className="notice-text">
          AgentGuard reads the local git repository and creates a review Case. If provided,
          the test command executes locally from the repo path with the backend's 120 second
          timeout. v0.1 does not modify code or apply AI fixes.
        </p>
        <button type="submit" disabled={!repoPath.trim() || !baseRef.trim() || loading}>
          {loading ? "Reviewing..." : "Run review"}
        </button>
      </form>

      <section className="panel">
        <div className="section-heading">
          <h2>Review result</h2>
          {result && (
            <Link className="secondary-action" to={`/cases/${result.case_id}`}>
              Open Case
            </Link>
          )}
        </div>
        {!result && <p className="muted">No review run yet.</p>}
        {result && (
          <>
            <div className="chip-row">
              <span className={`status-pill risk-${result.risk_level}`}>
                Risk {result.risk_level}
              </span>
              <span className={`status-pill ${testFailed ? "warn" : "ok"}`}>
                Test {testStatus}
              </span>
            </div>
            {testFailed && (
              <p className="error-text">
                The test command completed as a review finding. The Case was created and the
                failure is recorded as evidence.
              </p>
            )}
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
                <dt>Claims</dt>
                <dd>{result.claims_created}</dd>
              </div>
              <div>
                <dt>Evidence</dt>
                <dd>{result.evidence_created}</dd>
              </div>
              <div>
                <dt>Test command</dt>
                <dd className="mono-cell">{testCommandText}</dd>
              </div>
              <div>
                <dt>Return code</dt>
                <dd>{testReturnCode}</dd>
              </div>
            </dl>

            <div className="two-column">
              <div>
                <h3>Changed files</h3>
                {result.changed_files.length === 0 ? (
                  <p className="muted">No changed files detected.</p>
                ) : (
                  <ul className="compact-list">
                    {result.changed_files.map((file) => (
                      <li className="mono-cell" key={file}>
                        {file}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div>
                <h3>Artifacts</h3>
                {result.artifacts.length === 0 ? (
                  <p className="muted">No artifacts returned.</p>
                ) : (
                  <ul className="compact-list">
                    {result.artifacts.map((artifact) => (
                      <li key={artifact.id}>
                        <strong>{artifact.name}</strong>{" "}
                        <span className="muted">({artifact.kind})</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
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

function metadataText(metadata: JsonObject | undefined, key: string): string {
  if (!metadata) return "not recorded";
  const value = metadata[key];
  if (value === null || value === undefined) return "not recorded";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}

function reviewErrorText(error: unknown): string {
  const message = formatApiError(error);
  const lower = message.toLowerCase();
  if (lower.includes("git") || lower.includes("repo")) {
    return `AgentGuard could not inspect this git repository: ${message}`;
  }
  if (lower.includes("test command executable not found")) {
    return `AgentGuard could not run the local test command: ${message}`;
  }
  if (lower.includes("base_ref") || lower.includes("base ref")) {
    return `AgentGuard could not resolve the base ref: ${message}`;
  }
  return `AgentGuard review failed: ${message}`;
}
