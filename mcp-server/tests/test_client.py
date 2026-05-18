"""Tests for ProofFlowClient HTTP wrapper."""

import json

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
async def test_triage_issue_success(client):
    respx.post("http://127.0.0.1:8787/issue-triage").mock(
        return_value=httpx.Response(200, json={
            "case_id": "case-issue",
            "run_id": "run-issue",
            "risk_level": "medium",
            "artifact_id": "artifact-issue",
            "component": "mcp_server",
            "suggested_labels": ["bug", "component:mcp_server"],
            "has_reproduction_steps": False,
            "has_expected_behavior": False,
            "has_environment_details": True,
            "claims_created": 4,
            "evidence_created": 4,
        })
    )
    result = await client.triage_issue(
        title="MCP tool fails",
        body="Environment: Windows 11",
        labels=["bug"],
    )
    assert result["case_id"] == "case-issue"
    assert result["component"] == "mcp_server"


@pytest.mark.asyncio
@respx.mock
async def test_start_work_contract(client):
    route = respx.post("http://127.0.0.1:8787/ledger/start").mock(
        return_value=httpx.Response(200, json={
            "case_id": "case-ledger",
            "status": "active",
            "case": {
                "id": "case-ledger",
                "title": "Implement MCP ledger tools",
                "kind": "agent_work_ledger",
                "status": "active",
                "summary": None,
                "metadata": {},
                "created_at": "t",
                "updated_at": "t",
            },
        })
    )
    result = await client.start_work_contract(
        objective="Implement MCP ledger tools",
        repo_path="D:/ProofFlow v0.1",
        allowed_scope=["mcp-server"],
        required_tests=["pytest"],
    )
    payload = json.loads(route.calls.last.request.content)
    assert result["case_id"] == "case-ledger"
    assert payload["allowed_scope"] == ["mcp-server"]
    assert payload["required_tests"] == ["pytest"]
    assert payload["forbidden_actions"] == []
    assert payload["algorithm_requirements"] == []
    assert payload["cost_budget"] == {}


@pytest.mark.asyncio
@respx.mock
async def test_record_event(client):
    route = respx.post("http://127.0.0.1:8787/ledger/cases/c1/events").mock(
        return_value=httpx.Response(200, json={
            "case_id": "c1",
            "artifact_id": "artifact-event",
            "sequence": 1,
            "event_type": "progress",
            "name": "progress-001",
            "created_at": "t",
        })
    )
    result = await client.record_event(
        case_id="c1",
        event_type="progress",
        summary="Added client methods",
        metadata={"phase": "implementation"},
    )
    payload = json.loads(route.calls.last.request.content)
    assert result["artifact_id"] == "artifact-event"
    assert payload["content"] == ""
    assert payload["metadata"] == {"phase": "implementation"}


@pytest.mark.asyncio
@respx.mock
async def test_record_algorithm_decision(client):
    route = respx.post("http://127.0.0.1:8787/ledger/cases/c1/algorithm-decisions").mock(
        return_value=httpx.Response(200, json={
            "case_id": "c1",
            "artifact_id": "artifact-algorithm",
            "sequence": 1,
            "summary": "Reuse timestamps",
            "name": "ledger-algorithm-decision-001.md",
            "created_at": "t",
        })
    )
    result = await client.record_algorithm_decision(
        case_id="c1",
        summary="Reuse timestamps",
        chosen_approach="Remap existing subtitle timestamps",
        rationale="Avoid rerunning ASR",
        forbidden_approaches=["Full retranscription"],
    )
    payload = json.loads(route.calls.last.request.content)
    assert result["artifact_id"] == "artifact-algorithm"
    assert payload["chosen_approach"] == "Remap existing subtitle timestamps"
    assert payload["forbidden_approaches"] == ["Full retranscription"]


@pytest.mark.asyncio
@respx.mock
async def test_record_cost_budget(client):
    route = respx.post("http://127.0.0.1:8787/ledger/cases/c1/cost-budgets").mock(
        return_value=httpx.Response(200, json={
            "case_id": "c1",
            "artifact_id": "artifact-budget",
            "sequence": 1,
            "summary": "No GPU ASR",
            "name": "ledger-cost-budget-001.md",
            "created_at": "t",
        })
    )
    result = await client.record_cost_budget(
        case_id="c1",
        summary="No GPU ASR",
        budget={"max_gpu_jobs": 0},
        limits=["Do not run Whisper after trimming"],
    )
    payload = json.loads(route.calls.last.request.content)
    assert result["artifact_id"] == "artifact-budget"
    assert payload["budget"] == {"max_gpu_jobs": 0}
    assert payload["limits"] == ["Do not run Whisper after trimming"]


@pytest.mark.asyncio
@respx.mock
async def test_capture_snapshot(client):
    respx.post("http://127.0.0.1:8787/ledger/cases/c1/snapshots").mock(
        return_value=httpx.Response(200, json={
            "case_id": "c1",
            "artifact_id": "artifact-snapshot",
            "phase": "checkpoint",
            "head_sha": "abc123",
            "base_ref": "HEAD",
            "changed_files": ["mcp-server/src/proofflow_mcp/client.py"],
            "diff_sha256": "sha",
        })
    )
    result = await client.capture_snapshot(
        case_id="c1",
        repo_path="D:/ProofFlow v0.1",
        phase="checkpoint",
    )
    assert result["phase"] == "checkpoint"
    assert result["changed_files"] == ["mcp-server/src/proofflow_mcp/client.py"]


@pytest.mark.asyncio
@respx.mock
async def test_record_evidence(client):
    route = respx.post("http://127.0.0.1:8787/ledger/cases/c1/evidence").mock(
        return_value=httpx.Response(200, json={
            "case_id": "c1",
            "artifact_id": "artifact-evidence",
            "evidence_id": "ev-1",
            "evidence_type": "command_output",
            "created_at": "t",
        })
    )
    result = await client.record_evidence(
        case_id="c1",
        evidence_type="command_output",
        content="pytest passed",
        source_ref="mcp-server/tests/test_client.py",
    )
    payload = json.loads(route.calls.last.request.content)
    assert result["evidence_id"] == "ev-1"
    assert payload["source_ref"] == "mcp-server/tests/test_client.py"


@pytest.mark.asyncio
@respx.mock
async def test_record_claim(client):
    route = respx.post("http://127.0.0.1:8787/ledger/cases/c1/claims").mock(
        return_value=httpx.Response(200, json={
            "case_id": "c1",
            "claim_id": "claim-1",
            "evidence_ids": ["ev-1"],
            "created_at": "t",
        })
    )
    result = await client.record_claim(
        case_id="c1",
        claim_text="MCP tools are covered by tests",
        severity="low",
        evidence_ids=["ev-1"],
    )
    payload = json.loads(route.calls.last.request.content)
    assert result["claim_id"] == "claim-1"
    assert payload["severity"] == "low"


@pytest.mark.asyncio
@respx.mock
async def test_evaluate_contract(client):
    respx.post("http://127.0.0.1:8787/ledger/cases/c1/evaluate").mock(
        return_value=httpx.Response(200, json={
            "case_id": "c1",
            "run_id": "run-1",
            "status": "passed",
            "passed": ["required_tests"],
            "failed": [],
            "warnings": [],
            "missing_evidence": [],
            "scope_violations": [],
            "risk_hints": [
                {
                    "code": "cost_budget_possible_overrun",
                    "severity": "medium",
                    "title": "Recorded usage appears to exceed the Cost Budget",
                    "message": "api_calls=3 > max_api_calls=0.",
                    "evidence": ["evidence:ev-1:test_output"],
                    "recommendation": "Review the usage metadata.",
                }
            ],
        })
    )
    result = await client.evaluate_contract("c1")
    assert result["status"] == "passed"
    assert result["passed"] == ["required_tests"]
    assert result["risk_hints"][0]["code"] == "cost_budget_possible_overrun"


@pytest.mark.asyncio
@respx.mock
async def test_finish_work_ledger(client):
    route = respx.post("http://127.0.0.1:8787/ledger/cases/c1/finish").mock(
        return_value=httpx.Response(200, json={
            "case_id": "c1",
            "status": "closed",
            "finished_at": "t",
            "metadata": {"evaluated": True},
        })
    )
    result = await client.finish_work_ledger("c1", summary="Done")
    payload = json.loads(route.calls.last.request.content)
    assert result["status"] == "closed"
    assert payload["summary"] == "Done"


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


@pytest.mark.asyncio
@respx.mock
async def test_create_decision(client):
    respx.post("http://127.0.0.1:8787/cases/c1/decisions").mock(
        return_value=httpx.Response(200, json={
            "id": "dec-1",
            "case_id": "c1",
            "title": "Approve gate",
            "status": "accepted",
            "rationale": "Safe to proceed",
            "result": "accepted",
            "metadata": {},
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        })
    )
    result = await client.create_decision(
        case_id="c1",
        title="Approve gate",
        status="accepted",
        rationale="Safe to proceed",
        result="accepted",
    )
    assert result["id"] == "dec-1"
    assert result["status"] == "accepted"
