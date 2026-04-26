import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiGet, formatApiError } from "../api/client";
import type { CaseResponse } from "../types";

export function Cases() {
  const [cases, setCases] = useState<CaseResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    apiGet<CaseResponse[]>("/cases")
      .then((response) => {
        if (!active) return;
        setCases(response);
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
  }, []);

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Cases</p>
          <h1>Case registry</h1>
        </div>
      </header>

      <div className="panel">
        {loading && <p className="muted">Loading cases...</p>}
        {error && <p className="error-text">{error}</p>}
        {!loading && !error && cases.length === 0 && <p className="muted">No cases found.</p>}
        {cases.length > 0 && (
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
                {cases.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <Link to={`/cases/${item.id}`}>{item.title}</Link>
                    </td>
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
