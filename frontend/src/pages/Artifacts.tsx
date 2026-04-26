import { useEffect, useState } from "react";
import { apiGet, formatApiError } from "../api/client";
import type { ArtifactResponse } from "../types";

function artifactPath(artifact: ArtifactResponse): string {
  const path = artifact.metadata.path;
  return typeof path === "string" ? path : artifact.uri;
}

export function Artifacts() {
  const [artifacts, setArtifacts] = useState<ArtifactResponse[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    apiGet<ArtifactResponse[]>("/artifacts")
      .then((response) => {
        if (!active) return;
        setArtifacts(response);
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
          <p className="eyebrow">Artifacts</p>
          <h1>Indexed local objects</h1>
        </div>
      </header>

      <div className="panel">
        {loading && <p className="muted">Loading artifacts...</p>}
        {error && <p className="error-text">{error}</p>}
        {!loading && !error && artifacts.length === 0 && (
          <p className="muted">No artifacts found.</p>
        )}
        {artifacts.length > 0 && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Kind</th>
                  <th>Path</th>
                  <th>Size</th>
                </tr>
              </thead>
              <tbody>
                {artifacts.map((artifact) => (
                  <tr key={artifact.id}>
                    <td>{artifact.name}</td>
                    <td>{artifact.kind}</td>
                    <td className="mono-cell">{artifactPath(artifact)}</td>
                    <td>{artifact.size_bytes ?? "n/a"}</td>
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
