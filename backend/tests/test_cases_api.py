from datetime import datetime
from uuid import UUID

from fastapi.testclient import TestClient

from proofflow.main import app


def _client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(tmp_path / "proofflow.db"))
    return TestClient(app)


def _assert_uuid(value: str) -> None:
    UUID(value)


def _assert_iso_timestamp(value: str) -> None:
    datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_create_list_get_and_update_case(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        create_response = client.post(
            "/cases",
            json={
                "title": "Local evidence review",
                "kind": "local_proof",
                "summary": "Initial case",
                "metadata": {"owner": "tester"},
            },
        )
        assert create_response.status_code == 201
        created = create_response.json()
        _assert_uuid(created["id"])
        _assert_iso_timestamp(created["created_at"])
        _assert_iso_timestamp(created["updated_at"])
        assert created["title"] == "Local evidence review"
        assert created["kind"] == "local_proof"
        assert created["status"] == "open"
        assert created["summary"] == "Initial case"
        assert created["metadata"] == {"owner": "tester"}

        list_response = client.get("/cases")
        assert list_response.status_code == 200
        assert [case["id"] for case in list_response.json()] == [created["id"]]

        get_response = client.get(f"/cases/{created['id']}")
        assert get_response.status_code == 200
        assert get_response.json() == {**created, "decision_count": 0}

        patch_response = client.patch(
            f"/cases/{created['id']}",
            json={
                "title": "Updated evidence review",
                "status": "active",
                "summary": None,
                "metadata": {"owner": "tester", "phase": "mvp"},
            },
        )
        assert patch_response.status_code == 200
        updated = patch_response.json()
        assert updated["id"] == created["id"]
        assert updated["title"] == "Updated evidence review"
        assert updated["kind"] == "local_proof"
        assert updated["status"] == "active"
        assert updated["summary"] is None
        assert updated["metadata"] == {"owner": "tester", "phase": "mvp"}


def test_case_missing_and_invalid_requests(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        assert client.get("/cases/missing").status_code == 404
        assert client.patch("/cases/missing", json={"status": "closed"}).status_code == 404
        assert client.patch("/cases/missing", json={}).status_code == 400

        invalid_status = client.patch("/cases/missing", json={"status": "blocked"})
        assert invalid_status.status_code == 422

        forbidden_kind = client.patch("/cases/missing", json={"kind": "agent_guard"})
        assert forbidden_kind.status_code == 422

        invalid_kind = client.post(
            "/cases",
            json={"title": "Bad case", "kind": "general"},
        )
        assert invalid_kind.status_code == 422
