import type { FormEvent } from "react";
import { useState } from "react";
import { apiGet, apiPatch, apiPost, formatApiError } from "../api/client";
import type { DecisionResponse, DecisionStatus } from "../types";

const statuses: DecisionStatus[] = ["proposed", "accepted", "rejected", "superseded"];

export function Decisions() {
  const [caseId, setCaseId] = useState("");
  const [decisions, setDecisions] = useState<DecisionResponse[]>([]);
  const [createTitle, setCreateTitle] = useState("");
  const [createStatus, setCreateStatus] = useState<DecisionStatus>("proposed");
  const [createRationale, setCreateRationale] = useState("");
  const [createResult, setCreateResult] = useState("");
  const [updateId, setUpdateId] = useState("");
  const [updateStatus, setUpdateStatus] = useState<DecisionStatus>("accepted");
  const [error, setError] = useState<string | null>(null);

  function loadDecisions() {
    if (!caseId.trim()) return;
    apiGet<DecisionResponse[]>(`/cases/${caseId}/decisions`)
      .then((response) => {
        setDecisions(response);
        setError(null);
      })
      .catch((requestError: unknown) => setError(formatApiError(requestError)));
  }

  function createDecision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    apiPost<DecisionResponse>(`/cases/${caseId}/decisions`, {
      title: createTitle,
      status: createStatus,
      rationale: createRationale,
      result: createResult,
    })
      .then(() => {
        setCreateTitle("");
        setCreateRationale("");
        setCreateResult("");
        loadDecisions();
      })
      .catch((requestError: unknown) => setError(formatApiError(requestError)));
  }

  function updateDecision(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    apiPatch<DecisionResponse>(`/decisions/${updateId}`, { status: updateStatus })
      .then(() => {
        loadDecisions();
        setError(null);
      })
      .catch((requestError: unknown) => setError(formatApiError(requestError)));
  }

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Decisions</p>
          <h1>Human decisions</h1>
        </div>
      </header>

      {error && <p className="error-text">{error}</p>}

      <div className="panel form-grid">
        <label>
          Case ID
          <input value={caseId} onChange={(event) => setCaseId(event.target.value)} />
        </label>
        <button type="button" onClick={loadDecisions} disabled={!caseId.trim()}>
          Load decisions
        </button>
      </div>

      <div className="two-column">
        <form className="panel form-grid" onSubmit={createDecision}>
          <h2>Create decision</h2>
          <label>
            Title
            <input value={createTitle} onChange={(event) => setCreateTitle(event.target.value)} />
          </label>
          <label>
            Status
            <select
              value={createStatus}
              onChange={(event) => setCreateStatus(event.target.value as DecisionStatus)}
            >
              {statuses.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <label>
            Rationale
            <textarea
              value={createRationale}
              onChange={(event) => setCreateRationale(event.target.value)}
            />
          </label>
          <label>
            Result
            <textarea value={createResult} onChange={(event) => setCreateResult(event.target.value)} />
          </label>
          <button
            type="submit"
            disabled={
              !caseId.trim() ||
              !createTitle.trim() ||
              !createRationale.trim() ||
              !createResult.trim()
            }
          >
            Create
          </button>
        </form>

        <form className="panel form-grid" onSubmit={updateDecision}>
          <h2>Update status</h2>
          <label>
            Decision ID
            <input value={updateId} onChange={(event) => setUpdateId(event.target.value)} />
          </label>
          <label>
            Status
            <select
              value={updateStatus}
              onChange={(event) => setUpdateStatus(event.target.value as DecisionStatus)}
            >
              {statuses.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={!updateId.trim()}>
            Update
          </button>
        </form>
      </div>

      <div className="panel">
        <h2>Decision list</h2>
        {decisions.length === 0 ? (
          <p className="muted">No decisions loaded.</p>
        ) : (
          <ul className="stack-list">
            {decisions.map((decision) => (
              <li key={decision.id}>
                <strong>{decision.title}</strong>
                <span>{decision.id}</span>
                <span className="status-pill">{decision.status}</span>
                <span>{decision.result}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
