"""Tests for tool handler dispatch with mocked HTTP."""

import pytest
import httpx
import respx

from proofflow_mcp.server import call_tool


@pytest.mark.asyncio
@respx.mock
async def test_health_tool():
    respx.get("http://127.0.0.1:8787/health").mock(
        return_value=httpx.Response(200, json={
            "ok": True,
            "service": "proofflow",
            "version": "0.1.0",
            "release_stage": "stable",
            "release_name": "ProofFlow v0.1.0",
        })
    )
    result = await call_tool("proofflow_health", {})
    assert len(result) == 1
    assert "ProofFlow is running" in result[0].text
    assert "0.1.0" in result[0].text


@pytest.mark.asyncio
@respx.mock
async def test_scan_tool():
    respx.post("http://127.0.0.1:8787/localproof/scan").mock(
        return_value=httpx.Response(200, json={
            "case_id": "case-abc",
            "files_seen": 15,
            "artifacts_created": 12,
            "artifacts_updated": 0,
            "text_chunks_created": 8,
            "skipped": 3,
            "skipped_items": [{"path": "/tmp/big.bin", "reason": "too large", "indexed": False}],
        })
    )
    result = await call_tool("proofflow_scan", {"folder_path": "/tmp/test"})
    text = result[0].text
    assert "case-abc" in text
    assert "Files seen: 15" in text
    assert "Skipped: 3" in text
    assert "big.bin" in text


@pytest.mark.asyncio
@respx.mock
async def test_review_tool():
    respx.post("http://127.0.0.1:8787/agentguard/review").mock(
        return_value=httpx.Response(200, json={
            "case_id": "case-review",
            "run_id": "run-1",
            "risk_level": "medium",
            "changed_files": ["src/app.py", "tests/test_app.py"],
            "claims_created": 3,
            "evidence_created": 4,
            "artifacts": [],
        })
    )
    result = await call_tool("proofflow_review", {"repo_path": "/tmp/repo"})
    text = result[0].text
    assert "case-review" in text
    assert "medium" in text
    assert "src/app.py" in text


@pytest.mark.asyncio
@respx.mock
async def test_approve_execute_tool_preview_first():
    """Without confirmed_preview, tool returns preview without executing."""
    respx.post("http://127.0.0.1:8787/actions/act-1/approve").mock(
        return_value=httpx.Response(200, json={
            "id": "act-1", "case_id": "c1", "kind": "move_file",
            "status": "approved", "title": "Move readme", "reason": "organize",
            "preview": {"from_path": "/src/readme.md", "to_path": "/docs/readme.md"},
            "result": None, "undo": None,
            "metadata": {}, "created_at": "t", "updated_at": "t",
        })
    )
    result = await call_tool("proofflow_approve_execute", {"action_id": "act-1"})
    text = result[0].text
    assert "NOT yet executed" in text
    assert "/src/readme.md" in text
    assert "/docs/readme.md" in text
    assert "confirmed_preview=true" in text


@pytest.mark.asyncio
@respx.mock
async def test_approve_execute_tool_confirmed():
    """With confirmed_preview=true, tool approves and executes."""
    respx.post("http://127.0.0.1:8787/actions/act-1/approve").mock(
        return_value=httpx.Response(200, json={
            "id": "act-1", "case_id": "c1", "kind": "move_file",
            "status": "approved", "title": "Move", "reason": "org",
            "preview": {}, "result": None, "undo": None,
            "metadata": {}, "created_at": "t", "updated_at": "t",
        })
    )
    respx.post("http://127.0.0.1:8787/actions/act-1/execute").mock(
        return_value=httpx.Response(200, json={
            "id": "act-1", "case_id": "c1", "kind": "move_file",
            "status": "executed", "title": "Move", "reason": "org",
            "preview": {}, "result": {"moved": True}, "undo": {},
            "metadata": {}, "created_at": "t", "updated_at": "t",
        })
    )
    result = await call_tool(
        "proofflow_approve_execute",
        {"action_id": "act-1", "confirmed_preview": True},
    )
    text = result[0].text
    assert "executed successfully" in text


@pytest.mark.asyncio
@respx.mock
async def test_approve_execute_pending_decision():
    """Policy gate blocks execution even with confirmed_preview."""
    respx.post("http://127.0.0.1:8787/actions/act-2/approve").mock(
        return_value=httpx.Response(200, json={
            "id": "act-2", "case_id": "c1", "kind": "move_file",
            "status": "approved", "title": "Move", "reason": "org",
            "preview": {}, "result": None, "undo": None,
            "metadata": {}, "created_at": "t", "updated_at": "t",
        })
    )
    respx.post("http://127.0.0.1:8787/actions/act-2/execute").mock(
        return_value=httpx.Response(200, json={
            "id": "act-2", "case_id": "c1", "kind": "move_file",
            "status": "pending_decision", "title": "Move", "reason": "org",
            "preview": {}, "result": None, "undo": None,
            "metadata": {}, "created_at": "t", "updated_at": "t",
        })
    )
    result = await call_tool(
        "proofflow_approve_execute",
        {"action_id": "act-2", "confirmed_preview": True},
    )
    text = result[0].text
    assert "policy gate" in text
    assert "pending_decision" in text


@pytest.mark.asyncio
@respx.mock
async def test_error_returns_text():
    respx.get("http://127.0.0.1:8787/health").mock(side_effect=httpx.ConnectError("refused"))
    result = await call_tool("proofflow_health", {})
    text = result[0].text
    assert "Error:" in text
    assert "not running" in text


@pytest.mark.asyncio
async def test_unknown_tool():
    result = await call_tool("proofflow_nonexistent", {})
    assert "Unknown tool" in result[0].text


@pytest.mark.asyncio
@respx.mock
async def test_list_cases_tool():
    respx.get("http://127.0.0.1:8787/cases").mock(
        return_value=httpx.Response(200, json=[
            {"id": "c1", "title": "Test case", "kind": "local_proof",
             "status": "open", "summary": None, "metadata": {},
             "created_at": "t", "updated_at": "t"},
        ])
    )
    result = await call_tool("proofflow_list_cases", {})
    text = result[0].text
    assert "c1" in text
    assert "local_proof" in text


@pytest.mark.asyncio
@respx.mock
async def test_search_tool():
    respx.get("http://127.0.0.1:8787/search").mock(
        return_value=httpx.Response(200, json={
            "query": "hello",
            "results": [
                {"artifact_id": "a1", "chunk_id": "ch1", "name": "hello.py",
                 "path": "/src/hello.py", "snippet": "print('hello')",
                 "start_line": 1, "end_line": 1, "score": 0.9},
            ],
        })
    )
    result = await call_tool("proofflow_search", {"query": "hello"})
    text = result[0].text
    assert "hello.py" in text
    assert "0.90" in text


@pytest.mark.asyncio
@respx.mock
async def test_decide_tool():
    respx.get("http://127.0.0.1:8787/cases/c1/actions").mock(
        return_value=httpx.Response(200, json=[{
            "id": "act-1",
            "case_id": "c1",
            "kind": "move_file",
            "title": "Move file",
            "status": "pending_decision",
            "metadata": {
                "policy_gate": {
                    "pipeline_id": "pipe-123",
                    "preview_hash": "hash-456",
                }
            },
            "created_at": "t",
            "updated_at": "t",
        }])
    )
    respx.post("http://127.0.0.1:8787/cases/c1/decisions").mock(
        return_value=httpx.Response(200, json={
            "id": "dec-1",
            "case_id": "c1",
            "title": "Decision on action act-1",
            "status": "accepted",
            "rationale": "Reviewed and safe",
            "result": "accepted",
            "metadata": {"decision_kind": "policy_gate_owner_decision", "action_id": "act-1"},
            "created_at": "t",
            "updated_at": "t",
        })
    )
    result = await call_tool("proofflow_decide", {
        "case_id": "c1",
        "action_id": "act-1",
        "decision": "accepted",
        "rationale": "Reviewed and safe",
    })
    text = result[0].text
    assert "Decision created" in text
    assert "dec-1" in text
    assert "accepted" in text
