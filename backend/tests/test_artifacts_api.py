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


def _create_case(client: TestClient) -> dict:
    response = client.post(
        "/cases",
        json={"title": "AgentGuard review", "kind": "agent_guard"},
    )
    assert response.status_code == 201
    return response.json()


def _create_artifact(client: TestClient) -> dict:
    response = client.post(
        "/artifacts",
        json={
            "kind": "file",
            "uri": "local://README.md",
            "name": "README.md",
            "mime_type": "text/markdown",
            "sha256": "abc123",
            "size_bytes": 42,
            "metadata": {"source": "manual"},
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_list_and_get_artifact(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        created = _create_artifact(client)
        _assert_uuid(created["id"])
        _assert_iso_timestamp(created["created_at"])
        _assert_iso_timestamp(created["updated_at"])
        assert created["kind"] == "file"
        assert created["uri"] == "local://README.md"
        assert created["name"] == "README.md"
        assert created["mime_type"] == "text/markdown"
        assert created["sha256"] == "abc123"
        assert created["size_bytes"] == 42
        assert created["metadata"] == {"source": "manual"}

        list_response = client.get("/artifacts")
        assert list_response.status_code == 200
        assert [artifact["id"] for artifact in list_response.json()] == [created["id"]]

        get_response = client.get(f"/artifacts/{created['id']}")
        assert get_response.status_code == 200
        assert get_response.json() == created


def test_artifact_missing_and_invalid_kind(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        assert client.get("/artifacts/missing").status_code == 404

        invalid_kind = client.post(
            "/artifacts",
            json={"kind": "folder", "uri": "local://x", "name": "x"},
        )
        assert invalid_kind.status_code == 422


def test_link_artifact_to_case(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        case = _create_case(client)
        artifact = _create_artifact(client)

        default_link = client.post(f"/cases/{case['id']}/artifacts/{artifact['id']}")
        assert default_link.status_code == 201
        linked = default_link.json()
        assert linked["case_id"] == case["id"]
        assert linked["artifact_id"] == artifact["id"]
        assert linked["role"] == "supporting"
        _assert_iso_timestamp(linked["created_at"])
        _assert_iso_timestamp(linked["updated_at"])

        same_link = client.post(f"/cases/{case['id']}/artifacts/{artifact['id']}")
        assert same_link.status_code == 201
        assert same_link.json() == linked

        primary_link = client.post(
            f"/cases/{case['id']}/artifacts/{artifact['id']}",
            json={"role": "primary"},
        )
        assert primary_link.status_code == 201
        assert primary_link.json()["role"] == "primary"
        assert primary_link.json()["created_at"] == linked["created_at"]


def test_link_missing_resources(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        case = _create_case(client)
        artifact = _create_artifact(client)

        missing_case = client.post(f"/cases/missing/artifacts/{artifact['id']}")
        assert missing_case.status_code == 404

        missing_artifact = client.post(f"/cases/{case['id']}/artifacts/missing")
        assert missing_artifact.status_code == 404

        invalid_role = client.post(
            f"/cases/{case['id']}/artifacts/{artifact['id']}",
            json={"role": "owner"},
        )
        assert invalid_role.status_code == 422

