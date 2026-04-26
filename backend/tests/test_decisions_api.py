from datetime import datetime
from uuid import UUID

from fastapi.testclient import TestClient

from proofflow.main import app


def _client(monkeypatch, tmp_path) -> TestClient:
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(tmp_path / "decisions.db"))
    return TestClient(app)


def _create_case(client: TestClient) -> str:
    response = client.post(
        "/cases",
        json={"title": "Decision case", "kind": "local_proof"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _decision_payload(**overrides):
    payload = {
        "title": "Accept AgentGuard review after tests pass",
        "status": "accepted",
        "rationale": "Tests passed and all high-risk claims were resolved.",
        "result": "Proceed with commit.",
    }
    payload.update(overrides)
    return payload


def _assert_uuid(value: str) -> None:
    UUID(value)


def _assert_iso_timestamp(value: str) -> None:
    datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_create_list_update_decisions_and_case_detail_count(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        case_id = _create_case(client)

        create_response = client.post(
            f"/cases/{case_id}/decisions",
            json=_decision_payload(),
        )
        assert create_response.status_code == 201
        created = create_response.json()
        _assert_uuid(created["id"])
        _assert_iso_timestamp(created["created_at"])
        _assert_iso_timestamp(created["updated_at"])
        assert created["case_id"] == case_id
        assert created["status"] == "accepted"
        assert created["result"] == "Proceed with commit."

        second_response = client.post(
            f"/cases/{case_id}/decisions",
            json=_decision_payload(
                title="Choose SQLite for metadata DB",
                status="proposed",
                rationale="Local-first MVP needs a simple embedded database.",
                result="Use SQLite for v0.1.",
            ),
        )
        assert second_response.status_code == 201
        second = second_response.json()

        list_response = client.get(f"/cases/{case_id}/decisions")
        assert list_response.status_code == 200
        decisions = list_response.json()
        assert [decision["id"] for decision in decisions] == [second["id"], created["id"]]

        patch_response = client.patch(
            f"/decisions/{created['id']}",
            json={
                "title": "Supersede AgentGuard decision",
                "status": "superseded",
                "rationale": "A newer review packet replaced this decision.",
                "result": "Do not use this decision as current guidance.",
            },
        )
        assert patch_response.status_code == 200
        updated = patch_response.json()
        assert updated["id"] == created["id"]
        assert updated["status"] == "superseded"
        assert updated["title"] == "Supersede AgentGuard decision"
        assert updated["updated_at"] >= created["updated_at"]

        detail_response = client.get(f"/cases/{case_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["decision_count"] == 2


def test_decision_missing_resources_and_invalid_requests(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        case_id = _create_case(client)
        create_response = client.post(
            f"/cases/{case_id}/decisions",
            json=_decision_payload(),
        )
        assert create_response.status_code == 201
        decision_id = create_response.json()["id"]

        assert client.get("/cases/missing/decisions").status_code == 404
        assert client.post("/cases/missing/decisions", json=_decision_payload()).status_code == 404
        assert client.patch("/decisions/missing", json={"status": "accepted"}).status_code == 404
        assert client.patch(f"/decisions/{decision_id}", json={}).status_code == 400

        invalid_create = client.post(
            f"/cases/{case_id}/decisions",
            json=_decision_payload(status="approved"),
        )
        assert invalid_create.status_code == 422

        invalid_update = client.patch(
            f"/decisions/{decision_id}",
            json={"status": "approved"},
        )
        assert invalid_update.status_code == 422

        extra_field = client.post(
            f"/cases/{case_id}/decisions",
            json={**_decision_payload(), "actor": "tester"},
        )
        assert extra_field.status_code == 422

        null_update = client.patch(
            f"/decisions/{decision_id}",
            json={"result": None},
        )
        assert null_update.status_code == 422
