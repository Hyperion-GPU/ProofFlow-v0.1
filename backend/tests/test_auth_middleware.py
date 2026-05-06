"""Tests for OptionalAPIKeyMiddleware."""

from fastapi.testclient import TestClient

from proofflow.main import app


def test_no_auth_when_key_unset(monkeypatch, tmp_path):
    """All requests pass when PROOFFLOW_API_KEY is not set."""
    monkeypatch.delenv("PROOFFLOW_API_KEY", raising=False)
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(tmp_path / "test.db"))

    with TestClient(app) as client:
        response = client.get("/cases")
    assert response.status_code == 200


def test_401_when_key_set_but_header_missing(monkeypatch, tmp_path):
    """Returns 401 when API key is configured but request has no token."""
    monkeypatch.setenv("PROOFFLOW_API_KEY", "secret-key-123")
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(tmp_path / "test.db"))

    with TestClient(app) as client:
        response = client.get("/cases")
    assert response.status_code == 401
    assert "API key" in response.json()["detail"]


def test_401_when_key_set_but_header_wrong(monkeypatch, tmp_path):
    """Returns 401 when token doesn't match configured key."""
    monkeypatch.setenv("PROOFFLOW_API_KEY", "secret-key-123")
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(tmp_path / "test.db"))

    with TestClient(app) as client:
        response = client.get("/cases", headers={"X-ProofFlow-Token": "wrong"})
    assert response.status_code == 401


def test_pass_when_key_matches(monkeypatch, tmp_path):
    """Returns 200 when token matches configured key."""
    monkeypatch.setenv("PROOFFLOW_API_KEY", "secret-key-123")
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(tmp_path / "test.db"))

    with TestClient(app) as client:
        response = client.get(
            "/cases", headers={"X-ProofFlow-Token": "secret-key-123"}
        )
    assert response.status_code == 200


def test_health_always_public(monkeypatch, tmp_path):
    """Health endpoint passes without auth even when key is set."""
    monkeypatch.setenv("PROOFFLOW_API_KEY", "secret-key-123")
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(tmp_path / "test.db"))

    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["ok"] is True
