import { useEffect, useState } from "react";
import { API_BASE_URL, apiGet, formatApiError } from "../api/client";
import type { CaseResponse, HealthResponse } from "../types";

export function Dashboard() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [cases, setCases] = useState<CaseResponse[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.all([apiGet<HealthResponse>("/health"), apiGet<CaseResponse[]>("/cases")])
      .then(([healthResponse, caseResponse]) => {
        if (!active) return;
        setHealth(healthResponse);
        setCases(caseResponse);
        setError(null);
      })
      .catch((requestError: unknown) => {
        if (!active) return;
        setError(formatApiError(requestError));
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Dashboard</p>
          <h1>ProofFlow workspace</h1>
        </div>
        <span className={health?.ok ? "status-pill ok" : "status-pill warn"}>
          {health?.ok ? "Backend online" : "Backend unknown"}
        </span>
      </header>

      <div className="panel">
        <h2>Backend status</h2>
        {error ? (
          <p className="error-text">{error}</p>
        ) : (
          <dl className="detail-list">
            <div>
              <dt>API base URL</dt>
              <dd>{API_BASE_URL}</dd>
            </div>
            <div>
              <dt>Service</dt>
              <dd>{health?.service ?? "Loading"}</dd>
            </div>
            <div>
              <dt>Cases</dt>
              <dd>{cases.length}</dd>
            </div>
          </dl>
        )}
      </div>

      <div className="panel">
        <h2>Recent cases</h2>
        {cases.length === 0 ? (
          <p className="muted">No cases found.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Kind</th>
                  <th>Status</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {cases.slice(0, 5).map((item) => (
                  <tr key={item.id}>
                    <td>{item.title}</td>
                    <td>{item.kind}</td>
                    <td>{item.status}</td>
                    <td>{item.updated_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
