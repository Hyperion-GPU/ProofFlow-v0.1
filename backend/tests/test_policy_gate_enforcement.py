"""Tests for the policy gate runtime enforcement (Checkpoint H).

Covers the full decision gate lifecycle:
- High-risk action transitions to pending_decision on first execute
- Low-risk action executes immediately
- pending_decision action with valid accepted Decision executes
- pending_decision action without Decision raises error
- pending_decision action with rejected Decision raises error
- pending_decision action with mismatched context raises error
- Observer crash is fail-open (action executes)
- pending_decision action can be rejected
- Full lifecycle: create → approve → execute (paused) → decision → execute (succeeds)
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from proofflow.db import connect
from proofflow.main import app
from proofflow.services.json_utils import loads_metadata


def _client(monkeypatch, temp_root: Path) -> TestClient:
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(temp_root / "enforcement.db"))
    monkeypatch.setenv("PROOFFLOW_DATA_DIR", str(temp_root / "data"))
    return TestClient(app)


def _create_case(client: TestClient) -> str:
    response = client.post(
        "/cases",
        json={"title": "Enforcement test", "kind": "file_cleanup"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _scope_metadata(*roots: Path) -> dict:
    return {
        "scope_kind": "test_file_action",
        "allowed_roots": [str(root.resolve(strict=False)) for root in roots],
    }


def _create_move_action(client: TestClient, case_id: str, source: Path, dest: Path) -> dict:
    response = client.post(
        "/actions",
        json={
            "case_id": case_id,
            "kind": "move_file",
            "title": "Move file",
            "reason": "enforcement test",
            "preview": {
                "from_path": str(source),
                "to_path": str(dest),
            },
            "metadata": _scope_metadata(source.parent),
        },
    )
    assert response.status_code == 201
    return response.json()


def _get_action_metadata(action_id: str) -> dict:
    with connect() as connection:
        row = connection.execute(
            "SELECT metadata_json FROM actions WHERE id = ?",
            (action_id,),
        ).fetchone()
    return loads_metadata(row["metadata_json"])


def _create_policy_gate_decision(
    client: TestClient,
    case_id: str,
    action_id: str,
    *,
    policy_evaluation_id: str = "",
    preview_hash: str = "",
    accepted: bool = True,
) -> dict:
    """Create a Decision with policy gate metadata."""
    response = client.post(
        f"/cases/{case_id}/decisions",
        json={
            "title": "Policy gate decision",
            "status": "accepted" if accepted else "rejected",
            "rationale": "Owner reviewed and approved" if accepted else "Too risky",
            "result": "approved" if accepted else "rejected",
            "metadata": {
                "decision_kind": "policy_gate_owner_decision",
                "action_id": action_id,
                "policy_evaluation_id": policy_evaluation_id,
                "preview_hash": preview_hash,
            },
        },
    )
    assert response.status_code == 201
    return response.json()


class TestHighRiskPausesExecution:
    def test_move_file_transitions_to_pending_decision(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "file.txt"
            dest = temp_root / "moved.txt"
            source.write_text("content", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)
                action = _create_move_action(client, case_id, source, dest)

                client.post(f"/actions/{action['id']}/approve")
                result = client.post(f"/actions/{action['id']}/execute")

                assert result.status_code == 200
                assert result.json()["status"] == "pending_decision"
                assert source.exists()
                assert not dest.exists()

    def test_gate_metadata_stored_in_action(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "file.txt"
            dest = temp_root / "moved.txt"
            source.write_text("content", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)
                action = _create_move_action(client, case_id, source, dest)

                client.post(f"/actions/{action['id']}/approve")
                client.post(f"/actions/{action['id']}/execute")

                metadata = _get_action_metadata(action["id"])
                gate = metadata["policy_gate"]
                assert gate["status"] == "pending_decision"
                assert "pipeline_id" in gate
                assert "observation_id" in gate
                assert "preview_hash" in gate
                assert "categories" in gate
                assert "reason" in gate


class TestLowRiskExecutesImmediately:
    def test_manual_check_executes_without_gate(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)

                action = client.post(
                    "/actions",
                    json={
                        "case_id": case_id,
                        "kind": "manual_check",
                        "title": "Manual check",
                        "reason": "low risk test",
                        "metadata": {},
                    },
                ).json()

                client.post(f"/actions/{action['id']}/approve")
                result = client.post(f"/actions/{action['id']}/execute")

                assert result.status_code == 200
                assert result.json()["status"] == "executed"


class TestDecisionGateResolution:
    def test_accepted_decision_allows_execution(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "file.txt"
            dest = temp_root / "moved.txt"
            source.write_text("content", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)
                action = _create_move_action(client, case_id, source, dest)

                client.post(f"/actions/{action['id']}/approve")
                client.post(f"/actions/{action['id']}/execute")

                # Get gate metadata for decision binding
                metadata = _get_action_metadata(action["id"])
                gate = metadata["policy_gate"]

                # Create accepted decision with matching context
                _create_policy_gate_decision(
                    client,
                    case_id,
                    action["id"],
                    policy_evaluation_id=gate["pipeline_id"],
                    preview_hash=gate["preview_hash"],
                    accepted=True,
                )

                # Second execute resolves the gate
                result = client.post(f"/actions/{action['id']}/execute")
                assert result.status_code == 200
                assert result.json()["status"] == "executed"
                assert not source.exists()
                assert dest.read_text(encoding="utf-8") == "content"

    def test_no_decision_blocks_execution(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "file.txt"
            dest = temp_root / "moved.txt"
            source.write_text("content", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)
                action = _create_move_action(client, case_id, source, dest)

                client.post(f"/actions/{action['id']}/approve")
                client.post(f"/actions/{action['id']}/execute")

                # Try to execute without creating a decision
                result = client.post(f"/actions/{action['id']}/execute")
                assert result.status_code == 400
                assert source.exists()

    def test_rejected_decision_blocks_execution(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "file.txt"
            dest = temp_root / "moved.txt"
            source.write_text("content", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)
                action = _create_move_action(client, case_id, source, dest)

                client.post(f"/actions/{action['id']}/approve")
                client.post(f"/actions/{action['id']}/execute")

                metadata = _get_action_metadata(action["id"])
                gate = metadata["policy_gate"]

                # Create rejected decision
                _create_policy_gate_decision(
                    client,
                    case_id,
                    action["id"],
                    policy_evaluation_id=gate["pipeline_id"],
                    preview_hash=gate["preview_hash"],
                    accepted=False,
                )

                result = client.post(f"/actions/{action['id']}/execute")
                assert result.status_code == 400
                assert source.exists()

    def test_mismatched_preview_hash_blocks_execution(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "file.txt"
            dest = temp_root / "moved.txt"
            source.write_text("content", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)
                action = _create_move_action(client, case_id, source, dest)

                client.post(f"/actions/{action['id']}/approve")
                client.post(f"/actions/{action['id']}/execute")

                metadata = _get_action_metadata(action["id"])
                gate = metadata["policy_gate"]

                # Create decision with wrong preview_hash
                _create_policy_gate_decision(
                    client,
                    case_id,
                    action["id"],
                    policy_evaluation_id=gate["pipeline_id"],
                    preview_hash="wrong-hash",
                    accepted=True,
                )

                result = client.post(f"/actions/{action['id']}/execute")
                assert result.status_code == 400
                assert "preview_hash_mismatch" in result.json()["detail"]
                assert source.exists()


class TestFailOpenOnObserverCrash:
    def test_execution_proceeds_when_gate_check_crashes(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "file.txt"
            dest = temp_root / "moved.txt"
            source.write_text("content", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)
                action = _create_move_action(client, case_id, source, dest)

                client.post(f"/actions/{action['id']}/approve")

                with patch(
                    "proofflow.services.action_service._check_policy_gate_inner",
                    side_effect=RuntimeError("simulated crash"),
                ):
                    result = client.post(f"/actions/{action['id']}/execute")

                assert result.status_code == 200
                assert result.json()["status"] == "executed"
                assert not source.exists()
                assert dest.read_text(encoding="utf-8") == "content"


class TestPendingDecisionCanBeRejected:
    def test_reject_pending_decision_action(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "file.txt"
            dest = temp_root / "moved.txt"
            source.write_text("content", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)
                action = _create_move_action(client, case_id, source, dest)

                client.post(f"/actions/{action['id']}/approve")
                client.post(f"/actions/{action['id']}/execute")

                # Verify it's pending
                get_result = client.get(f"/cases/{case_id}/actions")
                assert get_result.json()[0]["status"] == "pending_decision"

                # Reject it
                reject_result = client.post(f"/actions/{action['id']}/reject")
                assert reject_result.status_code == 200
                assert reject_result.json()["status"] == "rejected"
                assert source.exists()


class TestEnforcementEvidenceRecorded:
    def test_enforcement_evidence_has_correct_type(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "file.txt"
            dest = temp_root / "moved.txt"
            source.write_text("content", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)
                action = _create_move_action(client, case_id, source, dest)

                client.post(f"/actions/{action['id']}/approve")
                client.post(f"/actions/{action['id']}/execute")

                with connect() as connection:
                    rows = connection.execute(
                        """
                        SELECT evidence_type, content, metadata_json
                        FROM evidence
                        WHERE case_id = ? AND evidence_type = ?
                        """,
                        (case_id, "policy_gate_enforcement"),
                    ).fetchall()

                assert len(rows) == 1
                meta = json.loads(rows[0]["metadata_json"])
                assert meta["enforcing"] is True
                assert meta["high_risk"] is True

                content = json.loads(rows[0]["content"])
                assert "pipeline_id" in content
                assert "snapshot" in content


class TestFullLifecycle:
    def test_create_approve_pause_decide_execute(self, monkeypatch):
        """Full lifecycle: create → approve → execute (paused) → decision → execute."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "important.txt"
            dest = temp_root / "archived.txt"
            source.write_text("important data", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)
                action = _create_move_action(client, case_id, source, dest)

                # Step 1: Approve
                approve_result = client.post(f"/actions/{action['id']}/approve")
                assert approve_result.json()["status"] == "approved"

                # Step 2: First execute → paused
                exec1 = client.post(f"/actions/{action['id']}/execute")
                assert exec1.json()["status"] == "pending_decision"
                assert source.exists()

                # Step 3: Create owner decision
                metadata = _get_action_metadata(action["id"])
                gate = metadata["policy_gate"]

                _create_policy_gate_decision(
                    client,
                    case_id,
                    action["id"],
                    policy_evaluation_id=gate["pipeline_id"],
                    preview_hash=gate["preview_hash"],
                    accepted=True,
                )

                # Step 4: Second execute → succeeds
                exec2 = client.post(f"/actions/{action['id']}/execute")
                assert exec2.status_code == 200
                assert exec2.json()["status"] == "executed"
                assert not source.exists()
                assert dest.read_text(encoding="utf-8") == "important data"
