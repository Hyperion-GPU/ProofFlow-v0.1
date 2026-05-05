"""Tests for the policy gate runtime observer."""

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


def _get_observation_evidence(case_id: str) -> list[dict]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, case_id, evidence_type, content, source_ref, metadata_json
            FROM evidence
            WHERE case_id = ? AND evidence_type = ?
            """,
            (case_id, "policy_gate_dry_run_observation"),
        ).fetchall()
    return [dict(row) for row in rows]


class TestHighRiskProducesEvidence:
    def test_move_file_creates_observation(self, monkeypatch):
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
                        "reason": "test observation",
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

                evidence = _get_observation_evidence(case_id)
                assert len(evidence) == 1

                content = json.loads(evidence[0]["content"])
                assert content["non_enforcing"] is True
                assert content["high_risk"] is True
                assert content["label"] == "observed_only"
                assert content["would_have_outcome"] == "warn"
                assert evidence[0]["source_ref"] == action["id"]


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

                evidence = _get_observation_evidence(case_id)
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
                    "proofflow.services.policy_gate_runtime_observer._observe_inner",
                    side_effect=RuntimeError("simulated observer crash"),
                ):
                    executed = client.post(f"/actions/{action['id']}/execute")

                assert executed.status_code == 200
                assert executed.json()["status"] == "executed"
                assert destination.read_text(encoding="utf-8") == "content"
                assert not source.exists()


class TestObserverDoesNotModifyAction:
    def test_action_state_unchanged_by_observer(self, monkeypatch):
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
                        "reason": "test state preservation",
                        "preview": {
                            "from_path": str(source),
                            "to_path": str(destination),
                        },
                        "metadata": _scope_metadata(temp_root),
                    },
                ).json()

                client.post(f"/actions/{action['id']}/approve")

                # Check state before execution
                before = client.get(f"/cases/{case_id}/actions").json()[0]
                assert before["status"] == "approved"
                assert before["result"] is None

                executed = client.post(f"/actions/{action['id']}/execute")
                assert executed.status_code == 200

                # Action transitioned normally
                after = executed.json()
                assert after["status"] == "executed"
                assert after["result"]["from_path"] == str(source)


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
                client.post(f"/actions/{action['id']}/execute")

                evidence = _get_observation_evidence(case_id)
                assert len(evidence) == 1

                content = json.loads(evidence[0]["content"])
                assert "pipeline_id" in content
                assert "observation" in content
                assert "snapshot" in content
                assert content["observation"]["label"] == "observed_only"
                assert content["observation"]["non_enforcing"] is True

                meta = json.loads(evidence[0]["metadata_json"])
                assert meta["source"] == "policy_gate_runtime_observer"
                assert meta["non_enforcing"] is True
                assert meta["high_risk"] is True
                assert "pipeline_id" in meta
                assert "observation_id" in meta


class TestIntegrationExecuteWithObservation:
    def test_full_lifecycle_with_observation(self, monkeypatch):
        """Execute action completes AND observation evidence exists."""
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

                # File move succeeded
                assert executed.status_code == 200
                assert not source.exists()
                assert destination.read_text(encoding="utf-8") == "hello"

                # Observation evidence was recorded
                evidence = _get_observation_evidence(case_id)
                assert len(evidence) == 1
                assert evidence[0]["source_ref"] == action["id"]


class TestIntegrationExecuteWithObserverError:
    def test_execute_succeeds_despite_observer_crash(self, monkeypatch):
        """Execute action succeeds even when observer raises."""
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
                    "proofflow.services.policy_gate_runtime_observer._observe_inner",
                    side_effect=Exception("total failure"),
                ):
                    executed = client.post(f"/actions/{action['id']}/execute")

                assert executed.status_code == 200
                assert not source.exists()
                assert destination.read_text(encoding="utf-8") == "hello"

                # No evidence since observer crashed
                evidence = _get_observation_evidence(case_id)
                assert len(evidence) == 0
