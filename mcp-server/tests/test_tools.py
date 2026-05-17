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
async def test_triage_issue_tool():
    respx.post("http://127.0.0.1:8787/issue-triage").mock(
        return_value=httpx.Response(200, json={
            "case_id": "case-issue",
            "run_id": "run-issue",
            "risk_level": "medium",
            "artifact_id": "artifact-issue",
            "component": "codex_plugin",
            "suggested_labels": ["bug", "component:codex_plugin"],
            "has_reproduction_steps": True,
            "has_expected_behavior": False,
            "has_environment_details": True,
            "claims_created": 5,
            "evidence_created": 5,
        })
    )
    result = await call_tool(
        "proofflow_triage_issue",
        {
            "title": "Codex plugin prompt is unclear",
            "body": "Steps to Reproduce\n1. Open Codex\n2. Run plugin\nEnvironment: Windows 11",
            "labels": ["bug"],
        },
    )
    text = result[0].text
    assert "case-issue" in text
    assert "codex_plugin" in text
    assert "Reproduction steps: True" in text


@pytest.mark.asyncio
@respx.mock
async def test_start_work_contract_tool():
    respx.post("http://127.0.0.1:8787/ledger/start").mock(
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
    result = await call_tool(
        "proofflow_start_work_contract",
        {
            "objective": "Implement MCP ledger tools",
            "repo_path": "D:/ProofFlow v0.1",
            "allowed_scope": ["mcp-server"],
        },
    )
    text = result[0].text
    assert "Agent Work Ledger started" in text
    assert "case-ledger" in text
    assert "D:/ProofFlow v0.1" in text


@pytest.mark.asyncio
@respx.mock
async def test_record_event_tool():
    respx.post("http://127.0.0.1:8787/ledger/cases/c1/events").mock(
        return_value=httpx.Response(200, json={
            "case_id": "c1",
            "artifact_id": "artifact-event",
            "sequence": 2,
            "event_type": "progress",
            "name": "progress-002",
            "created_at": "t",
        })
    )
    result = await call_tool(
        "proofflow_record_event",
        {"case_id": "c1", "event_type": "progress", "summary": "Added handlers"},
    )
    text = result[0].text
    assert "Ledger event recorded" in text
    assert "artifact-event" in text
    assert "Sequence: 2" in text


@pytest.mark.asyncio
@respx.mock
async def test_capture_snapshot_tool():
    respx.post("http://127.0.0.1:8787/ledger/cases/c1/snapshots").mock(
        return_value=httpx.Response(200, json={
            "case_id": "c1",
            "artifact_id": "artifact-snapshot",
            "phase": "checkpoint",
            "head_sha": "abc123",
            "base_ref": "HEAD",
            "changed_files": ["mcp-server/src/proofflow_mcp/server.py"],
            "diff_sha256": "diff-sha",
        })
    )
    result = await call_tool(
        "proofflow_capture_snapshot",
        {
            "case_id": "c1",
            "repo_path": "D:/ProofFlow v0.1",
            "phase": "checkpoint",
        },
    )
    text = result[0].text
    assert "Ledger snapshot captured" in text
    assert "abc123" in text
    assert "mcp-server/src/proofflow_mcp/server.py" in text


@pytest.mark.asyncio
@respx.mock
async def test_record_evidence_tool():
    respx.post("http://127.0.0.1:8787/ledger/cases/c1/evidence").mock(
        return_value=httpx.Response(200, json={
            "case_id": "c1",
            "artifact_id": "artifact-evidence",
            "evidence_id": "ev-1",
            "evidence_type": "command_output",
            "created_at": "t",
        })
    )
    result = await call_tool(
        "proofflow_record_evidence",
        {
            "case_id": "c1",
            "evidence_type": "command_output",
            "content": "pytest passed",
        },
    )
    text = result[0].text
    assert "Ledger evidence recorded" in text
    assert "ev-1" in text


@pytest.mark.asyncio
@respx.mock
async def test_record_claim_tool():
    respx.post("http://127.0.0.1:8787/ledger/cases/c1/claims").mock(
        return_value=httpx.Response(200, json={
            "case_id": "c1",
            "claim_id": "claim-1",
            "evidence_ids": ["ev-1"],
            "created_at": "t",
        })
    )
    result = await call_tool(
        "proofflow_record_claim",
        {
            "case_id": "c1",
            "claim_text": "Tests cover the new tools",
            "evidence_ids": ["ev-1"],
        },
    )
    text = result[0].text
    assert "Ledger claim recorded" in text
    assert "claim-1" in text
    assert "ev-1" in text


@pytest.mark.asyncio
@respx.mock
async def test_evaluate_contract_tool():
    respx.post("http://127.0.0.1:8787/ledger/cases/c1/evaluate").mock(
        return_value=httpx.Response(200, json={
            "case_id": "c1",
            "run_id": "run-1",
            "status": "needs_attention",
            "passed": ["scope"],
            "failed": ["required_tests"],
            "warnings": ["final snapshot missing"],
            "missing_evidence": ["pytest output"],
            "scope_violations": [],
        })
    )
    result = await call_tool("proofflow_evaluate_contract", {"case_id": "c1"})
    text = result[0].text
    assert "Ledger contract evaluated" in text
    assert "needs_attention" in text
    assert "required_tests" in text
    assert "pytest output" in text


@pytest.mark.asyncio
@respx.mock
async def test_finish_work_ledger_tool():
    respx.post("http://127.0.0.1:8787/ledger/cases/c1/finish").mock(
        return_value=httpx.Response(200, json={
            "case_id": "c1",
            "status": "closed",
            "finished_at": "t",
            "metadata": {"evaluated": True},
        })
    )
    result = await call_tool(
        "proofflow_finish_work_ledger",
        {"case_id": "c1", "summary": "Done"},
    )
    text = result[0].text
    assert "Agent Work Ledger finished" in text
    assert "closed" in text
    assert "evaluated" in text


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
