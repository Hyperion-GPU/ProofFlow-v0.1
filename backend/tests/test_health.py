from fastapi.testclient import TestClient

from proofflow.main import app


def test_health_starts_app_and_initializes_database(monkeypatch, tmp_path):
    db_path = tmp_path / "proofflow.db"
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(db_path))

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"ok": True, "service": "proofflow-backend"}
    assert db_path.exists()

