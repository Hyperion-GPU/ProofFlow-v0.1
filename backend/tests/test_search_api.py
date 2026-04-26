from pathlib import Path
import tempfile

from fastapi.testclient import TestClient

from proofflow.db import connect, new_uuid, utc_now_iso
from proofflow.main import app
from proofflow.migrations import init_db
from proofflow.services.json_utils import dumps_metadata


def _client(monkeypatch, temp_root: Path) -> TestClient:
    db_path = temp_root / "search.db"
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(db_path))
    init_db(str(db_path))
    _seed_search_data()
    return TestClient(app)


def _seed_search_data() -> dict[str, str]:
    now = utc_now_iso()
    artifact_id = new_uuid()
    proof_chunk_id = new_uuid()
    other_chunk_id = new_uuid()

    with connect() as connection:
        connection.execute(
            """
            INSERT INTO artifacts (
                id, artifact_type, uri, name, mime_type, sha256, size_bytes,
                metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                "text",
                "file:///C:/ProofFlow/sample.md",
                "sample.md",
                "text/markdown",
                "sha-search",
                120,
                dumps_metadata({"path": "C:/ProofFlow/sample.md"}),
                now,
                now,
            ),
        )

        proof_cursor = connection.execute(
            """
            INSERT INTO artifact_text_chunks (
                id, artifact_id, chunk_index, content, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                proof_chunk_id,
                artifact_id,
                0,
                "Proof packets need citation-first search results.",
                dumps_metadata({"start_line": 3, "end_line": 6}),
                now,
                now,
            ),
        )
        other_cursor = connection.execute(
            """
            INSERT INTO artifact_text_chunks (
                id, artifact_id, chunk_index, content, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                other_chunk_id,
                artifact_id,
                1,
                "Unrelated notes about local folders.",
                dumps_metadata({"start_line": 10, "end_line": 12}),
                now,
                now,
            ),
        )

        connection.execute(
            """
            INSERT INTO artifact_text_fts(rowid, content, artifact_id, chunk_index)
            VALUES (?, ?, ?, ?)
            """,
            (
                proof_cursor.lastrowid,
                "Proof packets need citation-first search results.",
                artifact_id,
                0,
            ),
        )
        connection.execute(
            """
            INSERT INTO artifact_text_fts(rowid, content, artifact_id, chunk_index)
            VALUES (?, ?, ?, ?)
            """,
            (
                other_cursor.lastrowid,
                "Unrelated notes about local folders.",
                artifact_id,
                1,
            ),
        )
        connection.commit()

    return {"artifact_id": artifact_id, "proof_chunk_id": proof_chunk_id}


def test_search_returns_citation_result(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        with _client(monkeypatch, Path(temp_dir)) as client:
            response = client.get("/search", params={"q": "proof"})

        assert response.status_code == 200
        payload = response.json()
        assert payload["query"] == "proof"
        assert len(payload["results"]) == 1
        result = payload["results"][0]
        assert result["name"] == "sample.md"
        assert result["path"] == "C:/ProofFlow/sample.md"
        assert result["start_line"] == 3
        assert result["end_line"] == 6
        assert "proof" in result["snippet"].lower()
        assert result["artifact_id"]
        assert result["chunk_id"]
        assert isinstance(result["score"], float)


def test_search_returns_empty_results_for_no_match(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        with _client(monkeypatch, Path(temp_dir)) as client:
            response = client.get("/search", params={"q": "missing"})

    assert response.status_code == 200
    assert response.json() == {"query": "missing", "results": []}


def test_search_rejects_empty_or_unsearchable_query(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        with _client(monkeypatch, Path(temp_dir)) as client:
            empty_response = client.get("/search", params={"q": ""})
            punctuation_response = client.get("/search", params={"q": "!!!"})

    assert empty_response.status_code == 400
    assert punctuation_response.status_code == 400


def test_search_sanitizes_fts_syntax_and_honors_limit(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        with _client(monkeypatch, Path(temp_dir)) as client:
            syntax_response = client.get("/search", params={"q": 'proof:"', "limit": 1})
            too_large_limit = client.get("/search", params={"q": "proof", "limit": 26})

    assert syntax_response.status_code == 200
    assert len(syntax_response.json()["results"]) == 1
    assert too_large_limit.status_code == 422

