from fastapi.testclient import TestClient

from proofflow.config import get_db_path
from proofflow.db import connect
from proofflow.main import app
from proofflow.services.json_utils import dumps_metadata


def _client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(tmp_path / "case-packet.db"))
    return TestClient(app)


def _seed_case_packet() -> str:
    case_id = "case-packet-1"
    artifact_id = "artifact-packet-1"
    claim_id = "claim-packet-1"
    evidence_id = "evidence-packet-1"
    action_id = "action-packet-1"
    decision_id = "decision-packet-1"
    run_id = "run-packet-1"
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
                "Packet detail case",
                "code_review",
                "open",
                "Review the changed files and test output.",
                dumps_metadata({}),
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
                "file:///C:/ProofFlow/repo/app.py",
                "app.py diff",
                "text/plain",
                "sha-packet",
                128,
                dumps_metadata({"path": "C:/ProofFlow/repo/app.py"}),
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
                        "test_status": "failed",
                        "test_command": "python -m pytest",
                        "return_code": 1,
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
                "Tests failed during AgentGuard review.",
                "agentguard_risk",
                "open",
                dumps_metadata({"severity": "high"}),
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
                "AssertionError: expected safe action state",
                "tests/test_actions.py:42",
                dumps_metadata({}),
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
                "approved",
                "Inspect failed tests",
                "Inspect failed tests",
                "Tests failed and need a human check.",
                dumps_metadata({}),
                None,
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
                "Reject change until tests pass",
                "rejected",
                "High severity test failure remains.",
                "Do not commit.",
                dumps_metadata({}),
                now,
                now,
            ),
        )
        connection.commit()
    return case_id


def test_get_case_packet_returns_case_context(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        case_id = _seed_case_packet()
        response = client.get(f"/cases/{case_id}/packet")

    assert response.status_code == 200
    payload = response.json()
    assert payload["case"]["id"] == case_id
    assert payload["case"]["title"] == "Packet detail case"
    assert payload["case"]["decision_count"] == 1
    assert payload["risk_level"] == "high"

    assert len(payload["artifacts"]) == 1
    artifact = payload["artifacts"][0]
    assert artifact["name"] == "app.py diff"
    assert artifact["role"] == "primary"
    assert artifact["path"] == "C:/ProofFlow/repo/app.py"
    assert artifact["sha256"] == "sha-packet"

    assert len(payload["claims"]) == 1
    claim = payload["claims"][0]
    assert claim["severity"] == "high"
    assert claim["claim_text"] == "Tests failed during AgentGuard review."
    assert claim["evidence"][0]["content"] == "AssertionError: expected safe action state"
    assert claim["evidence"][0]["artifact_name"] == "app.py diff"
    assert claim["evidence"][0]["artifact_path"] == "C:/ProofFlow/repo/app.py"
    assert claim["evidence"][0]["source_ref"] == "tests/test_actions.py:42"

    assert payload["actions"][0]["status"] == "approved"
    assert payload["actions"][0]["title"] == "Inspect failed tests"
    assert payload["decisions"][0]["status"] == "rejected"
    assert payload["decisions"][0]["result"] == "Do not commit."
    assert payload["runs"][0]["metadata"]["test_status"] == "failed"
    assert payload["runs"][0]["metadata"]["return_code"] == 1


def test_get_case_packet_missing_case_returns_404(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        response = client.get("/cases/missing/packet")

    assert response.status_code == 404
