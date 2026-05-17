import json
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from proofflow.config import get_db_path
from proofflow.db import connect
from proofflow.main import app


def _client(monkeypatch, temp_root: Path) -> TestClient:
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(temp_root / "issue-triage.db"))
    monkeypatch.setenv("PROOFFLOW_DATA_DIR", str(temp_root / "data"))
    return TestClient(app)


def _claim_evidence_text(case_id: str) -> str:
    with connect(get_db_path()) as connection:
        rows = connection.execute(
            """
            SELECT claims.claim_text, evidence.content
            FROM claims
            JOIN evidence ON evidence.claim_id = claims.id
            WHERE claims.case_id = ?
            ORDER BY claims.created_at ASC, claims.id ASC
            """,
            (case_id,),
        ).fetchall()
    return "\n".join(f"{row['claim_text']}\n{row['content']}" for row in rows)


def test_issue_triage_creates_case_artifact_claims_and_packet(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        issue_body = (
            "Steps to Reproduce\n"
            "1. Open LocalProof\n"
            "2. Approve a policy gate action\n"
            "Expected Behavior\n"
            "The Execute button should become available after owner decision.\n"
            "Environment\n"
            "- OS: Windows 11\n"
            "- Node: 22.x\n"
        )

        with _client(monkeypatch, temp_root) as client:
            response = client.post(
                "/issue-triage",
                json={
                    "title": "Policy gate Execute button remains disabled",
                    "body": issue_body,
                    "source_url": "https://github.com/example/repo/issues/123",
                    "labels": ["bug", "ux", "bug"],
                },
            )
            assert response.status_code == 200
            payload = response.json()
            packet_response = client.post(
                f"/reports/cases/{payload['case_id']}/export",
                json={"format": "markdown"},
            )

        assert payload["risk_level"] == "info"
        assert payload["component"] == "localproof"
        assert payload["has_reproduction_steps"] is True
        assert payload["has_expected_behavior"] is True
        assert payload["has_environment_details"] is True
        assert payload["claims_created"] == payload["evidence_created"]
        assert payload["claims_created"] >= 5
        assert "component:localproof" in payload["suggested_labels"]

        with connect(get_db_path()) as connection:
            case = connection.execute(
                "SELECT case_type, metadata_json FROM cases WHERE id = ?",
                (payload["case_id"],),
            ).fetchone()
            artifact = connection.execute(
                """
                SELECT artifacts.artifact_type, artifacts.uri, artifacts.metadata_json,
                       artifact_text_chunks.content
                FROM artifacts
                JOIN case_artifacts ON case_artifacts.artifact_id = artifacts.id
                JOIN artifact_text_chunks ON artifact_text_chunks.artifact_id = artifacts.id
                WHERE case_artifacts.case_id = ?
                """,
                (payload["case_id"],),
            ).fetchone()

        assert case["case_type"] == "issue_triage"
        metadata = json.loads(case["metadata_json"])
        assert metadata["source_url"] == "https://github.com/example/repo/issues/123"
        assert metadata["labels"] == ["bug", "ux"]
        assert metadata["component"] == "localproof"
        assert artifact["artifact_type"] == "issue"
        assert artifact["uri"].startswith("issue-triage://")
        assert "Policy gate Execute button remains disabled" in artifact["content"]

        evidence_text = _claim_evidence_text(payload["case_id"])
        assert "Issue source captured for triage" in evidence_text
        assert "Issue includes reproduction steps" in evidence_text
        assert "Issue includes expected behavior context" in evidence_text
        assert "Issue includes environment details" in evidence_text

        assert packet_response.status_code == 200
        packet_text = packet_response.json()["content"]
        assert "Workflow type: `issue_triage`" in packet_text
        assert "Issue source captured for triage" in packet_text


def test_issue_triage_flags_incomplete_bug_report(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        with _client(monkeypatch, temp_root) as client:
            response = client.post(
                "/issue-triage",
                json={
                    "title": "MCP review tool fails",
                    "body": "It fails when I run it.",
                    "labels": ["bug"],
                },
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["risk_level"] == "medium"
        assert payload["component"] == "mcp_server"
        assert payload["has_reproduction_steps"] is False
        assert payload["has_expected_behavior"] is False

        evidence_text = _claim_evidence_text(payload["case_id"])
        assert "Bug-like issue is missing clear reproduction steps." in evidence_text
        assert "Bug-like issue is missing expected behavior context." in evidence_text
