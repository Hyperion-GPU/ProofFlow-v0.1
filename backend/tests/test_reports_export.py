from pathlib import Path

from fastapi.testclient import TestClient

from proofflow.config import get_db_path
from proofflow.db import connect
from proofflow.main import app
from proofflow.services.json_utils import dumps_metadata


def _client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(tmp_path / "reports.db"))
    monkeypatch.setenv("PROOFFLOW_DATA_DIR", str(tmp_path / "data"))
    return TestClient(app)


def _seed_packet_case() -> str:
    case_id = "case-report-1"
    artifact_id = "artifact-source-1"
    claim_id = "claim-1"
    evidence_id = "evidence-1"
    action_id = "action-1"
    decision_id = "decision-1"
    run_id = "run-1"
    now = "2026-01-01T00:00:00Z"

    with connect(get_db_path()) as connection:
        connection.execute(
            """
            INSERT INTO cases (
                id, title, case_type, status, summary, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                "Packet case",
                "code_review",
                "open",
                "Review and decide whether to proceed.",
                "{}",
                now,
                now,
            ),
        )
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
                "git_diff",
                "file:///C:/ProofFlow/source.py",
                "source.py",
                "text/plain",
                "sha-source",
                42,
                dumps_metadata({"path": "C:/ProofFlow/source.py"}),
                now,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO case_artifacts (
                case_id, artifact_id, role, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (case_id, artifact_id, "primary", now, now),
        )
        connection.execute(
            """
            INSERT INTO runs (
                id, case_id, run_type, status, started_at, finished_at,
                metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                case_id,
                "agentguard_review",
                "completed",
                now,
                now,
                dumps_metadata(
                    {
                        "test_status": "passed",
                        "test_command": "python -m pytest",
                        "risk_level": "medium",
                    }
                ),
                now,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO claims (
                id, case_id, run_id, claim_text, claim_type, status,
                metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim_id,
                case_id,
                run_id,
                "File operation code changed without test changes.",
                "agentguard_risk",
                "open",
                dumps_metadata({"severity": "medium"}),
                now,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO evidence (
                id, case_id, artifact_id, claim_id, evidence_type, content,
                source_ref, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_id,
                case_id,
                artifact_id,
                claim_id,
                "git_diff",
                "Evidence quote: shutil.move changed in source.py",
                "source.py:12",
                dumps_metadata({"source": "test"}),
                now,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO actions (
                id, case_id, run_id, action_type, status, description, title, reason,
                preview_json, result_json, undo_json, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_id,
                case_id,
                run_id,
                "manual_check",
                "executed",
                "Review risky change",
                "Review risky change",
                "Need human approval.",
                dumps_metadata({}),
                dumps_metadata({"touched_files": False}),
                None,
                dumps_metadata({}),
                now,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO decisions (
                id, case_id, title, status, rationale, result,
                metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                case_id,
                "Accept code change",
                "accepted",
                "Tests passed after review.",
                "Proceed with commit.",
                dumps_metadata({}),
                now,
                now,
            ),
        )
        connection.commit()

    return case_id


def test_export_case_proof_packet_writes_markdown_and_report_artifact(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        case_id = _seed_packet_case()
        response = client.post(
            f"/reports/cases/{case_id}/export",
            json={"format": "markdown"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["case_id"] == case_id
    assert payload["format"] == "markdown"
    assert payload["filename"].endswith(".md")
    report_path = Path(payload["path"])
    assert report_path.exists()
    assert report_path.parent == (tmp_path / "data" / "proof_packets")
    assert report_path.read_text(encoding="utf-8") == payload["content"]

    content = payload["content"]
    assert "Packet case" in content
    assert "File operation code changed without test changes." in content
    assert "Evidence quote: shutil.move changed in source.py" in content
    assert "C:/ProofFlow/source.py" in content
    assert "Review risky change" in content
    assert "executed" in content
    assert "Accept code change" in content
    assert "python -m pytest" in content
    assert "Remaining Risks" in content

    with connect(get_db_path()) as connection:
        artifact = connection.execute(
            """
            SELECT id, artifact_type, uri, name, mime_type, sha256, size_bytes, metadata_json
            FROM artifacts
            WHERE id = ?
            """,
            (payload["artifact_id"],),
        ).fetchone()
        link = connection.execute(
            """
            SELECT role
            FROM case_artifacts
            WHERE case_id = ? AND artifact_id = ?
            """,
            (case_id, payload["artifact_id"]),
        ).fetchone()

    assert artifact["artifact_type"] == "proof_packet"
    assert artifact["mime_type"] == "text/markdown"
    assert artifact["uri"].startswith("file:")
    assert artifact["sha256"]
    assert artifact["size_bytes"] == len(payload["content"].encode("utf-8"))
    assert '"source":"proof_packet_export"' in artifact["metadata_json"]
    assert link["role"] == "reference"


def test_export_case_proof_packet_does_not_overwrite_existing_report(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        case_id = _seed_packet_case()
        first = client.post(
            f"/reports/cases/{case_id}/export",
            json={"format": "markdown"},
        )
        second = client.post(
            f"/reports/cases/{case_id}/export",
            json={"format": "markdown"},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    first_payload = first.json()
    second_payload = second.json()
    assert first_payload["path"] != second_payload["path"]
    assert Path(first_payload["path"]).exists()
    assert Path(second_payload["path"]).exists()


def test_export_case_proof_packet_rejects_missing_case_and_unsupported_format(
    monkeypatch,
    tmp_path,
):
    with _client(monkeypatch, tmp_path) as client:
        missing = client.post(
            "/reports/cases/missing/export",
            json={"format": "markdown"},
        )
        invalid_format = client.post(
            "/reports/cases/missing/export",
            json={"format": "json"},
        )

    assert missing.status_code == 404
    assert invalid_format.status_code == 422
