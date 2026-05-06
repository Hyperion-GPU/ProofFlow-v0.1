"""Tests for ProofFlowClient HTTP wrapper."""

import pytest
import httpx
import respx

from proofflow_mcp.client import ProofFlowClient, ProofFlowError


@pytest.fixture
def client():
    return ProofFlowClient()


@pytest.mark.asyncio
@respx.mock
async def test_health_success(client):
    respx.get("http://127.0.0.1:8787/health").mock(
        return_value=httpx.Response(200, json={
            "ok": True,
            "service": "proofflow",
            "version": "0.1.0",
            "release_stage": "stable",
            "release_name": "ProofFlow v0.1.0",
        })
    )
    result = await client.health()
    assert result["ok"] is True
    assert result["version"] == "0.1.0"


@pytest.mark.asyncio
@respx.mock
async def test_health_backend_not_running(client):
    respx.get("http://127.0.0.1:8787/health").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(ProofFlowError, match="not running"):
        await client.health()


@pytest.mark.asyncio
@respx.mock
async def test_scan_success(client):
    respx.post("http://127.0.0.1:8787/localproof/scan").mock(
        return_value=httpx.Response(200, json={
            "case_id": "case-123",
            "files_seen": 10,
            "artifacts_created": 8,
            "artifacts_updated": 0,
            "text_chunks_created": 5,
            "skipped": 2,
            "skipped_items": [],
        })
    )
    result = await client.scan("/tmp/test")
    assert result["case_id"] == "case-123"
    assert result["files_seen"] == 10


@pytest.mark.asyncio
@respx.mock
async def test_scan_bad_path(client):
    respx.post("http://127.0.0.1:8787/localproof/scan").mock(
        return_value=httpx.Response(400, json={"detail": "Path does not exist"})
    )
    with pytest.raises(ProofFlowError, match="Path does not exist"):
        await client.scan("/nonexistent")


@pytest.mark.asyncio
@respx.mock
async def test_review_success(client):
    respx.post("http://127.0.0.1:8787/agentguard/review").mock(
        return_value=httpx.Response(200, json={
            "case_id": "case-456",
            "run_id": "run-1",
            "risk_level": "low",
            "changed_files": ["src/main.py"],
            "claims_created": 2,
            "evidence_created": 3,
            "artifacts": [],
        })
    )
    result = await client.review("/tmp/repo")
    assert result["risk_level"] == "low"
    assert result["changed_files"] == ["src/main.py"]


@pytest.mark.asyncio
@respx.mock
async def test_approve_action(client):
    respx.post("http://127.0.0.1:8787/actions/act-1/approve").mock(
        return_value=httpx.Response(200, json={
            "id": "act-1",
            "case_id": "case-1",
            "kind": "move_file",
            "status": "approved",
            "title": "Move file",
            "reason": "organize",
            "preview": {"from_path": "/a", "to_path": "/b"},
            "result": None,
            "undo": None,
            "metadata": {},
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        })
    )
    result = await client.approve_action("act-1")
    assert result["status"] == "approved"


@pytest.mark.asyncio
@respx.mock
async def test_search(client):
    respx.get("http://127.0.0.1:8787/search").mock(
        return_value=httpx.Response(200, json={
            "query": "test",
            "results": [
                {
                    "artifact_id": "art-1",
                    "chunk_id": "chunk-1",
                    "name": "test.py",
                    "path": "/src/test.py",
                    "snippet": "def test_something():",
                    "start_line": 1,
                    "end_line": 5,
                    "score": 0.95,
                }
            ],
        })
    )
    result = await client.search("test")
    assert len(result["results"]) == 1
    assert result["results"][0]["name"] == "test.py"


@pytest.mark.asyncio
@respx.mock
async def test_timeout(client):
    respx.get("http://127.0.0.1:8787/health").mock(side_effect=httpx.ReadTimeout("timeout"))
    with pytest.raises(ProofFlowError, match="timed out"):
        await client.health()


@pytest.mark.asyncio
@respx.mock
async def test_404_error(client):
    respx.get("http://127.0.0.1:8787/cases/bad-id/packet").mock(
        return_value=httpx.Response(404, json={"detail": "Case not found"})
    )
    with pytest.raises(ProofFlowError, match="Case not found"):
        await client.get_case_packet("bad-id")
