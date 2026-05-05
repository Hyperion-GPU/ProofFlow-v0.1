"""Tests for the policy gate runtime observer.

With enforcement active, high-risk actions transition to pending_decision
instead of executing immediately. These tests verify:
- High-risk actions produce enforcement evidence and pause
- Low-risk actions execute immediately with no evidence
- Observer failures are fail-open (action executes)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from proofflow.db import connect
from proofflow.main import app


def _client(monkeypatch, temp_root: Path) -> TestClient:
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(temp_root / "observer.db"))
    monkeypatch.setenv("PROOFFLOW_DATA_DIR", str(temp_root / "data"))
    return TestClient(app)


def _create_case(client: TestClient) -> str:
    response = client.post(
        "/cases",
        json={"title": "Observer test", "kind": "file_cleanup"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _scope_metadata(*roots: Path) -> dict:
    return {
        "scope_kind": "test_file_action",
        "allowed_roots": [str(root.resolve(strict=False)) for root in roots],
    }


def _get_enforcement_evidence(case_id: str) -> list[dict]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, case_id, evidence_type, content, source_ref, metadata_json
            FROM evidence
            WHERE case_id = ? AND evidence_type = ?
            """,
            (case_id, "policy_gate_enforcement"),
        ).fetchall()
    return [dict(row) for row in rows]


class TestHighRiskTransitionsToPendingDecision:
    def test_move_file_pauses_at_pending_decision(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "file.txt"
            destination = temp_root / "moved.txt"
            source.write_text("content", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)

                action = client.post(
                    "/actions",
                    json={
                        "case_id": case_id,
                        "kind": "move_file",
                        "title": "Move file",
                        "reason": "test enforcement",
                        "preview": {
                            "from_path": str(source),
                            "to_path": str(destination),
                        },
                        "metadata": _scope_metadata(temp_root),
                    },
                ).json()

                client.post(f"/actions/{action['id']}/approve")
                executed = client.post(f"/actions/{action['id']}/execute")
                assert executed.status_code == 200
                assert executed.json()["status"] == "pending_decision"

                # File was NOT moved
                assert source.exists()
                assert not destination.exists()

    def test_enforcement_evidence_recorded(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "file.txt"
            destination = temp_root / "moved.txt"
            source.write_text("content", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)

                action = client.post(
                    "/actions",
                    json={
                        "case_id": case_id,
                        "kind": "move_file",
                        "title": "Move file",
                        "reason": "test evidence",
                        "preview": {
                            "from_path": str(source),
                            "to_path": str(destination),
                        },
                        "metadata": _scope_metadata(temp_root),
                    },
                ).json()

                client.post(f"/actions/{action['id']}/approve")
                client.post(f"/actions/{action['id']}/execute")

                evidence = _get_enforcement_evidence(case_id)
                assert len(evidence) == 1
                assert evidence[0]["source_ref"] == action["id"]

                meta = json.loads(evidence[0]["metadata_json"])
                assert meta["enforcing"] is True
                assert meta["high_risk"] is True
                assert meta["source"] == "policy_gate_runtime_observer"


class TestLowRiskNoEvidence:
    def test_manual_check_no_observation(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)

                response = client.post(
                    "/actions",
                    json={
                        "case_id": case_id,
                        "kind": "manual_check",
                        "title": "Manual check",
                        "reason": "test no observation",
                        "metadata": {},
                    },
                )
                assert response.status_code == 201
                action = response.json()

                client.post(f"/actions/{action['id']}/approve")
                executed = client.post(f"/actions/{action['id']}/execute")
                assert executed.status_code == 200
                assert executed.json()["status"] == "executed"

                evidence = _get_enforcement_evidence(case_id)
                assert len(evidence) == 0


class TestObserverFailureDoesNotBlock:
    def test_execution_proceeds_on_observer_error(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "file.txt"
            destination = temp_root / "moved.txt"
            source.write_text("content", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)

                action = client.post(
                    "/actions",
                    json={
                        "case_id": case_id,
                        "kind": "move_file",
                        "title": "Move file",
                        "reason": "test fail-open",
                        "preview": {
                            "from_path": str(source),
                            "to_path": str(destination),
                        },
                        "metadata": _scope_metadata(temp_root),
                    },
                ).json()

                client.post(f"/actions/{action['id']}/approve")

                with patch(
                    "proofflow.services.action_service._check_policy_gate_inner",
                    side_effect=RuntimeError("simulated observer crash"),
                ):
                    executed = client.post(f"/actions/{action['id']}/execute")

                assert executed.status_code == 200
                assert executed.json()["status"] == "executed"
                assert destination.read_text(encoding="utf-8") == "content"
                assert not source.exists()


class TestEvidenceContentFields:
    def test_evidence_has_expected_structure(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "file.txt"
            destination = temp_root / "moved.txt"
            source.write_text("content", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)

                action = client.post(
                    "/actions",
                    json={
                        "case_id": case_id,
                        "kind": "move_file",
                        "title": "Move file",
                        "reason": "test evidence fields",
                        "preview": {
                            "from_path": str(source),
                            "to_path": str(destination),
                        },
                        "metadata": _scope_metadata(temp_root),
                    },
                ).json()

                client.post(f"/actions/{action['id']}/approve")
                result = client.post(f"/actions/{action['id']}/execute")
                assert result.json()["status"] == "pending_decision"

                evidence = _get_enforcement_evidence(case_id)
                assert len(evidence) == 1

                content = json.loads(evidence[0]["content"])
                assert "pipeline_id" in content
                assert "observation" in content
                assert "snapshot" in content

                meta = json.loads(evidence[0]["metadata_json"])
                assert meta["source"] == "policy_gate_runtime_observer"
                assert meta["enforcing"] is True
                assert meta["high_risk"] is True
                assert "pipeline_id" in meta
                assert "observation_id" in meta


class TestIntegrationEnforcementPause:
    def test_full_lifecycle_pauses_high_risk(self, monkeypatch):
        """High-risk action pauses at pending_decision, file not moved."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "file.txt"
            destination = temp_root / "moved.txt"
            source.write_text("hello", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)

                action = client.post(
                    "/actions",
                    json={
                        "case_id": case_id,
                        "kind": "move_file",
                        "title": "Move file",
                        "reason": "integration test",
                        "preview": {
                            "from_path": str(source),
                            "to_path": str(destination),
                        },
                        "metadata": _scope_metadata(temp_root),
                    },
                ).json()

                client.post(f"/actions/{action['id']}/approve")
                executed = client.post(f"/actions/{action['id']}/execute")

                # Action paused
                assert executed.status_code == 200
                assert executed.json()["status"] == "pending_decision"

                # File NOT moved
                assert source.exists()
                assert not destination.exists()

                # Enforcement evidence was recorded
                evidence = _get_enforcement_evidence(case_id)
                assert len(evidence) == 1
                assert evidence[0]["source_ref"] == action["id"]


class TestIntegrationExecuteWithObserverError:
    def test_execute_succeeds_despite_observer_crash(self, monkeypatch):
        """Execute action succeeds even when policy gate raises."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "file.txt"
            destination = temp_root / "moved.txt"
            source.write_text("hello", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)

                action = client.post(
                    "/actions",
                    json={
                        "case_id": case_id,
                        "kind": "move_file",
                        "title": "Move file",
                        "reason": "crash test",
                        "preview": {
                            "from_path": str(source),
                            "to_path": str(destination),
                        },
                        "metadata": _scope_metadata(temp_root),
                    },
                ).json()

                client.post(f"/actions/{action['id']}/approve")

                with patch(
                    "proofflow.services.action_service._check_policy_gate_inner",
                    side_effect=Exception("total failure"),
                ):
                    executed = client.post(f"/actions/{action['id']}/execute")

                assert executed.status_code == 200
                assert executed.json()["status"] == "executed"
                assert not source.exists()
                assert destination.read_text(encoding="utf-8") == "hello"

                # No evidence since observer crashed
                evidence = _get_enforcement_evidence(case_id)
                assert len(evidence) == 0
