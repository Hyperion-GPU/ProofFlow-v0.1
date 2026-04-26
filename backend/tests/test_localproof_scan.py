from pathlib import Path
import tempfile

from fastapi.testclient import TestClient

from proofflow.config import get_db_path
from proofflow.db import connect
from proofflow.services.text_extractor import MAX_TEXT_EXTRACTION_BYTES
from proofflow.main import app


def _client(monkeypatch, temp_root: Path) -> TestClient:
    db_path = temp_root / "db" / "proofflow.db"
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(db_path))
    return TestClient(app)


def _make_scan_folder(temp_root: Path) -> Path:
    folder = temp_root / "scan-me"
    folder.mkdir()
    (folder / "notes.md").write_text("# Notes\nhello local proof\n", encoding="utf-8")
    (folder / "script.py").write_text("print('hello')\n", encoding="utf-8")
    (folder / "pixel.png").write_bytes(b"\x89PNG\r\n\x1a\n")

    large_text = folder / "large.txt"
    with large_text.open("wb") as handle:
        handle.seek(MAX_TEXT_EXTRACTION_BYTES)
        handle.write(b"x")

    return folder


def _fetch_counts() -> dict[str, int]:
    with connect(get_db_path()) as connection:
        return {
            "cases": connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0],
            "artifacts": connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0],
            "case_artifacts": connection.execute(
                "SELECT COUNT(*) FROM case_artifacts"
            ).fetchone()[0],
            "chunks": connection.execute(
                "SELECT COUNT(*) FROM artifact_text_chunks"
            ).fetchone()[0],
            "fts": connection.execute("SELECT COUNT(*) FROM artifact_text_fts").fetchone()[0],
        }


def test_localproof_scan_indexes_files_and_extracts_text(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        folder = _make_scan_folder(temp_root)

        with _client(monkeypatch, temp_root) as client:
            response = client.post(
                "/localproof/scan",
                json={"folder_path": str(folder), "recursive": True, "max_files": 500},
            )

        assert response.status_code == 200
        summary = response.json()
        assert summary["files_seen"] == 4
        assert summary["artifacts_created"] == 4
        assert summary["artifacts_updated"] == 0
        assert summary["text_chunks_created"] == 2
        assert summary["skipped"] == 1
        assert summary["skipped_items"][0]["reason"] == "text_too_large"
        assert summary["skipped_items"][0]["indexed"] is True

        with connect(get_db_path()) as connection:
            case = connection.execute(
                "SELECT id, case_type, status FROM cases WHERE id = ?",
                (summary["case_id"],),
            ).fetchone()
            artifact_rows = connection.execute(
                "SELECT artifact_type, name, sha256, uri FROM artifacts ORDER BY name"
            ).fetchall()
            chunk_rows = connection.execute(
                """
                SELECT artifact_id, chunk_index, metadata_json
                FROM artifact_text_chunks
                ORDER BY chunk_index
                """
            ).fetchall()
            fts_hits = connection.execute(
                "SELECT COUNT(*) FROM artifact_text_fts WHERE artifact_text_fts MATCH 'hello'"
            ).fetchone()[0]

        assert case["case_type"] == "file_cleanup"
        assert case["status"] == "open"
        assert len(artifact_rows) == 4
        assert {row["artifact_type"] for row in artifact_rows} == {"code", "image", "text"}
        assert all(row["sha256"] for row in artifact_rows)
        assert all(row["uri"].startswith("file:") for row in artifact_rows)
        assert len(chunk_rows) == 2
        assert fts_hits >= 1

        counts = _fetch_counts()
        assert counts == {
            "cases": 1,
            "artifacts": 4,
            "case_artifacts": 4,
            "chunks": 2,
            "fts": 2,
        }


def test_localproof_scan_second_run_updates_artifacts_and_rebuilds_chunks(
    monkeypatch,
):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        folder = _make_scan_folder(temp_root)

        with _client(monkeypatch, temp_root) as client:
            first_response = client.post(
                "/localproof/scan",
                json={"folder_path": str(folder), "recursive": True, "max_files": 500},
            )
            assert first_response.status_code == 200

            second_response = client.post(
                "/localproof/scan",
                json={"folder_path": str(folder), "recursive": True, "max_files": 500},
            )

        assert second_response.status_code == 200
        summary = second_response.json()
        assert summary["files_seen"] == 4
        assert summary["artifacts_created"] == 0
        assert summary["artifacts_updated"] == 4
        assert summary["text_chunks_created"] == 2
        assert summary["skipped"] == 1

        counts = _fetch_counts()
        assert counts == {
            "cases": 2,
            "artifacts": 4,
            "case_artifacts": 8,
            "chunks": 2,
            "fts": 2,
        }


def test_localproof_scan_rejects_missing_folder(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        with _client(monkeypatch, temp_root) as client:
            response = client.post(
                "/localproof/scan",
                json={"folder_path": str(temp_root / "missing"), "recursive": True},
            )

    assert response.status_code == 400
