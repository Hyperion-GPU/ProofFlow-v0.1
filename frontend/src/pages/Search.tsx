import type { FormEvent } from "react";
import { useState } from "react";
import { apiGet, formatApiError } from "../api/client";
import type { SearchResponse } from "../types";

export function Search() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function runSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const params = new URLSearchParams({ q: query });
    setLoading(true);
    apiGet<SearchResponse>(`/search?${params.toString()}`)
      .then((response) => {
        setResult(response);
        setError(null);
      })
      .catch((requestError: unknown) => {
        setError(formatApiError(requestError));
      })
      .finally(() => setLoading(false));
  }

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Search</p>
          <h1>Citation search</h1>
        </div>
      </header>

      <form className="panel form-grid" onSubmit={runSearch}>
        <label>
          Query
          <input value={query} onChange={(event) => setQuery(event.target.value)} />
        </label>
        <button type="submit" disabled={loading || !query.trim()}>
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {error && <p className="error-text">{error}</p>}

      <div className="panel">
        <h2>Results</h2>
        {!result && <p className="muted">Enter a query to search indexed chunks.</p>}
        {result && result.results.length === 0 && <p className="muted">No matches.</p>}
        {result && result.results.length > 0 && (
          <ul className="result-list">
            {result.results.map((item) => (
              <li key={item.chunk_id}>
                <div className="result-meta">
                  <strong>{item.name}</strong>
                  <span>
                    lines {item.start_line}-{item.end_line}
                  </span>
                </div>
                <p>{item.snippet}</p>
                <span className="mono-cell">{item.path ?? item.artifact_id}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
