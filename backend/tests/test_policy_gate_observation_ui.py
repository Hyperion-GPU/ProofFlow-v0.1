"""Tests for policy gate observation display in case packet response."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from proofflow.main import app


def _client(monkeypatch, temp_root: Path) -> TestClient:
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(temp_root / "obs-ui.db"))
    monkeypatch.setenv("PROOFFLOW_DATA_DIR", str(temp_root / "data"))
    return TestClient(app)


def _create_case(client: TestClient) -> str:
    response = client.post(
        "/cases",
        json={"title": "Observation UI test", "kind": "file_cleanup"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _scope_metadata(*roots: Path) -> dict:
    return {
        "scope_kind": "test_file_action",
        "allowed_roots": [str(root.resolve(strict=False)) for root in roots],
    }


class TestNoObservations:
    def test_empty_observations_for_case_without_high_risk(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)

                packet = client.get(f"/cases/{case_id}/packet")
                assert packet.status_code == 200

                data = packet.json()
                assert "observations" in data
                assert data["observations"] == []


class TestObservationPresent:
    def test_move_file_produces_observation_in_packet(self, monkeypatch):
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
                        "reason": "test observation ui",
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

                packet = client.get(f"/cases/{case_id}/packet")
                assert packet.status_code == 200

                data = packet.json()
                observations = data["observations"]
                assert len(observations) == 1

                obs = observations[0]
                assert obs["action_id"] == action["id"]
                assert obs["action_type"] == "move_file"
                assert obs["high_risk"] is True
                assert obs["non_enforcing"] is False
                assert obs["would_have_outcome"] == "require_decision"
                assert "destructive_local_operation" in obs["categories"]
                assert obs["label"] == "enforced"
                assert "created_at" in obs


class TestObservationFields:
    def test_observation_has_all_expected_keys(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            source = temp_root / "a.txt"
            destination = temp_root / "b.txt"
            source.write_text("x", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)

                action = client.post(
                    "/actions",
                    json={
                        "case_id": case_id,
                        "kind": "move_file",
                        "title": "Move",
                        "reason": "fields test",
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

                packet = client.get(f"/cases/{case_id}/packet").json()
                obs = packet["observations"][0]

                expected_keys = {
                    "id",
                    "action_id",
                    "action_type",
                    "high_risk",
                    "non_enforcing",
                    "would_have_outcome",
                    "categories",
                    "label",
                    "created_at",
                }
                assert set(obs.keys()) == expected_keys


class TestMultipleObservations:
    def test_multiple_actions_produce_multiple_observations(self, monkeypatch):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            file_a = temp_root / "a.txt"
            file_b = temp_root / "b.txt"
            dest_a = temp_root / "moved_a.txt"
            dest_b = temp_root / "moved_b.txt"
            file_a.write_text("a", encoding="utf-8")
            file_b.write_text("b", encoding="utf-8")

            with _client(monkeypatch, temp_root) as client:
                case_id = _create_case(client)

                action_a = client.post(
                    "/actions",
                    json={
                        "case_id": case_id,
                        "kind": "move_file",
                        "title": "Move A",
                        "reason": "multi test",
                        "preview": {
                            "from_path": str(file_a),
                            "to_path": str(dest_a),
                        },
                        "metadata": _scope_metadata(temp_root),
                    },
                ).json()

                action_b = client.post(
                    "/actions",
                    json={
                        "case_id": case_id,
                        "kind": "move_file",
                        "title": "Move B",
                        "reason": "multi test",
                        "preview": {
                            "from_path": str(file_b),
                            "to_path": str(dest_b),
                        },
                        "metadata": _scope_metadata(temp_root),
                    },
                ).json()

                client.post(f"/actions/{action_a['id']}/approve")
                result_a = client.post(f"/actions/{action_a['id']}/execute")
                assert result_a.json()["status"] == "pending_decision"

                client.post(f"/actions/{action_b['id']}/approve")
                result_b = client.post(f"/actions/{action_b['id']}/execute")
                assert result_b.json()["status"] == "pending_decision"

                packet = client.get(f"/cases/{case_id}/packet").json()
                observations = packet["observations"]
                assert len(observations) == 2

                action_ids = {obs["action_id"] for obs in observations}
                assert action_a["id"] in action_ids
                assert action_b["id"] in action_ids
