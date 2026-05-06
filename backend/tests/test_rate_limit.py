"""Tests for SimpleRateLimitMiddleware."""

from fastapi.testclient import TestClient

from proofflow.main import app


def test_no_rate_limit_when_unset(monkeypatch, tmp_path):
    """All requests pass when PROOFFLOW_RATE_LIMIT is not set."""
    monkeypatch.delenv("PROOFFLOW_RATE_LIMIT", raising=False)
    monkeypatch.delenv("PROOFFLOW_API_KEY", raising=False)
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(tmp_path / "test.db"))

    with TestClient(app) as client:
        for _ in range(20):
            response = client.get("/health")
            assert response.status_code == 200


def test_429_after_limit_exceeded(monkeypatch, tmp_path):
    """Returns 429 after exceeding the configured rate limit."""
    monkeypatch.setenv("PROOFFLOW_RATE_LIMIT", "5")
    monkeypatch.delenv("PROOFFLOW_API_KEY", raising=False)
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(tmp_path / "test.db"))

    # Need to recreate app to pick up the new env var
    from proofflow.main import create_app

    test_app = create_app()

    with TestClient(test_app) as client:
        # First 5 should pass
        for i in range(5):
            response = client.get("/health")
            assert response.status_code == 200, f"Request {i+1} failed unexpectedly"

        # 6th should be rate limited
        response = client.get("/health")
        assert response.status_code == 429
        assert "Rate limit" in response.json()["detail"]
