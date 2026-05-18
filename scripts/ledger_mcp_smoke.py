"""Smoke test the Agent Work Ledger MCP flow against the local backend app.

Starts the ProofFlow backend in-process with FastAPI TestClient, routes MCP
tool calls through the real tool handlers, and verifies the Ledger chain:

    health -> start contract -> algorithm decision -> cost budget -> snapshot ->
    event -> evidence -> claim -> evaluate -> finish -> export packet

Usage:
    python scripts/ledger_mcp_smoke.py [--cleanup]
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
MCP_SERVER_ROOT = REPO_ROOT / "mcp-server"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
if str(MCP_SERVER_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(MCP_SERVER_ROOT / "src"))


def run_smoke(temp_root: Path) -> dict[str, Any]:
    temp_root = temp_root.resolve()
    db_path = temp_root / "ledger-mcp-smoke.db"
    data_dir = temp_root / "data"
    repo = _init_repo(temp_root / "repo")
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    os.environ["PROOFFLOW_DB_PATH"] = str(db_path)
    os.environ["PROOFFLOW_DATA_DIR"] = str(data_dir)
    os.environ["PROOFFLOW_BASE_URL"] = "http://testserver"

    from fastapi.testclient import TestClient
    from proofflow.main import app
    from proofflow_mcp import server as mcp_server

    with TestClient(app) as test_client:
        patched_http = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda req: _sync_to_httpx_response(test_client, req)
            ),
            base_url="http://testserver",
        )
        mcp_server._client._http = patched_http
        mcp_server._client._base_url = "http://testserver"

        results = asyncio.run(_run_ledger_flow(repo))
        asyncio.run(patched_http.aclose())

    return {
        "db_path": str(db_path),
        "data_dir": str(data_dir),
        "repo_path": str(repo),
        **results,
    }


def _sync_to_httpx_response(
    test_client: Any,
    request: httpx.Request,
) -> httpx.Response:
    method = request.method.lower()
    parsed = urlparse(str(request.url))
    path = parsed.path
    if parsed.query:
        path = f"{path}?{parsed.query}"

    kwargs: dict[str, Any] = {}
    if request.content:
        kwargs["content"] = request.content
        kwargs["headers"] = dict(request.headers)

    response = getattr(test_client, method)(path, **kwargs)
    return httpx.Response(
        status_code=response.status_code,
        headers=dict(response.headers),
        content=response.content,
    )


async def _run_ledger_flow(repo: Path) -> dict[str, Any]:
    health = await _call("proofflow_health", {})
    _assert_contains(health, "ProofFlow is running")
    print("  [PASS] proofflow_health")

    start = await _call(
        "proofflow_start_work_contract",
        {
            "objective": "Ledger MCP smoke test",
            "repo_path": str(repo),
            "allowed_scope": ["app.py"],
            "forbidden_actions": ["delete user data", "remote sync", "cloud telemetry"],
            "required_tests": ["python -m pytest smoke"],
            "done_criteria": ["Ledger MCP smoke reaches ready_for_review"],
            "evidence_requirements": ["git_diff", "test_output"],
            "algorithm_requirements": ["record smoke algorithm decision"],
            "cost_budget": {"max_gpu_jobs": 0, "max_api_calls": 0},
        },
    )
    case_id = _extract_value(start, "Case ID")
    print(f"  [PASS] proofflow_start_work_contract -> {case_id}")

    algorithm = await _call(
        "proofflow_record_algorithm_decision",
        {
            "case_id": case_id,
            "summary": "Use direct file edit for smoke repo",
            "chosen_approach": "Modify app.py directly and verify with recorded test evidence.",
            "rationale": "The smoke repo is tiny and does not need generated or remote work.",
            "alternatives_considered": ["Run a model or external formatter service"],
            "invariants": ["No remote calls", "No GPU work"],
            "forbidden_approaches": ["External API calls"],
        },
    )
    _assert_contains(algorithm, "Ledger algorithm decision recorded.")
    print("  [PASS] proofflow_record_algorithm_decision")

    budget = await _call(
        "proofflow_record_cost_budget",
        {
            "case_id": case_id,
            "summary": "No remote or GPU cost for smoke flow",
            "budget": {"max_gpu_jobs": 0, "max_api_calls": 0},
            "expected_operations": ["local git diff", "local pytest evidence"],
            "limits": ["Do not call remote APIs", "Do not run GPU workloads"],
        },
    )
    _assert_contains(budget, "Ledger cost budget recorded.")
    print("  [PASS] proofflow_record_cost_budget")

    start_snapshot = await _call(
        "proofflow_capture_snapshot",
        {
            "case_id": case_id,
            "repo_path": str(repo),
            "phase": "start",
            "base_ref": "HEAD",
            "include_untracked": True,
        },
    )
    _assert_contains(start_snapshot, "Ledger snapshot captured.")
    _assert_contains(start_snapshot, "app.py")
    print("  [PASS] proofflow_capture_snapshot start")

    event = await _call(
        "proofflow_record_event",
        {
            "case_id": case_id,
            "event_type": "implementation",
            "summary": "Recorded smoke implementation event",
            "content": "Smoke test changed app.py in a temporary repository.",
            "metadata": {"file": "app.py"},
        },
    )
    _assert_contains(event, "Ledger event recorded.")
    print("  [PASS] proofflow_record_event")

    evidence = await _call(
        "proofflow_record_evidence",
        {
            "case_id": case_id,
            "evidence_type": "test_output",
            "content": "COMMAND: python -m pytest smoke\nRETURN_CODE: 0\n1 passed\n",
            "source_ref": "ledger_mcp_smoke.py",
            "metadata": {
                "command": "python -m pytest smoke",
                "returncode": 0,
            },
        },
    )
    evidence_id = _extract_value(evidence, "Evidence")
    print(f"  [PASS] proofflow_record_evidence -> {evidence_id}")

    claim = await _call(
        "proofflow_record_claim",
        {
            "case_id": case_id,
            "claim_text": "Ledger MCP smoke test passed.",
            "severity": "info",
            "evidence_ids": [evidence_id],
        },
    )
    _assert_contains(claim, "Ledger claim recorded.")
    print("  [PASS] proofflow_record_claim")

    final_snapshot = await _call(
        "proofflow_capture_snapshot",
        {
            "case_id": case_id,
            "repo_path": str(repo),
            "phase": "final",
            "base_ref": "HEAD",
            "include_untracked": True,
        },
    )
    _assert_contains(final_snapshot, "Phase: final")
    print("  [PASS] proofflow_capture_snapshot final")

    evaluation = await _call("proofflow_evaluate_contract", {"case_id": case_id})
    _assert_contains(evaluation, "Status: ready_for_review")
    print("  [PASS] proofflow_evaluate_contract -> ready_for_review")

    finish = await _call(
        "proofflow_finish_work_ledger",
        {
            "case_id": case_id,
            "summary": "Ledger MCP smoke completed successfully.",
        },
    )
    _assert_contains(finish, "Status: finished")
    print("  [PASS] proofflow_finish_work_ledger")

    packet = await _call("proofflow_export_packet", {"case_id": case_id})
    for expected in (
        "Proof Packet exported",
        "## Work Contract",
        "## Algorithm Decisions",
        "## Cost Budget",
        "## Ledger Timeline",
        "## Snapshots",
        "## Done Criteria Evaluation",
        "Ledger MCP smoke test passed.",
    ):
        _assert_contains(packet, expected)
    print("  [PASS] proofflow_export_packet")

    return {
        "case_id": case_id,
        "evidence_id": evidence_id,
        "evaluation_status": "ready_for_review",
    }


async def _call(name: str, args: dict[str, Any]) -> str:
    from proofflow_mcp.server import call_tool

    result = await call_tool(name, args)
    text = result[0].text
    if text.startswith("Error:"):
        raise RuntimeError(text)
    return text


def _extract_value(text: str, label: str) -> str:
    prefix = f"{label}:"
    for line in text.splitlines():
        if prefix in line:
            value = line.split(prefix, 1)[1].strip()
            if value:
                return value
    raise RuntimeError(f"could not find {label!r} in output:\n{text}")


def _assert_contains(text: str, expected: str) -> None:
    if expected not in text:
        raise AssertionError(f"expected {expected!r} in output:\n{text}")


def _init_repo(repo: Path) -> Path:
    if shutil.which("git") is None:
        raise RuntimeError("git executable was not found")

    repo.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "config", "user.email", "ledger-smoke@example.test")
    _git(repo, "config", "user.name", "Ledger Smoke")
    (repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")
    return repo


def _git(repo: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Work Ledger MCP smoke test")
    parser.add_argument("--cleanup", action="store_true", help="Remove temp files on success")
    args = parser.parse_args()

    temp_root = Path(tempfile.mkdtemp(prefix="proofflow-ledger-mcp-smoke-"))
    print("Agent Work Ledger MCP Smoke Test")
    print(f"  temp_root: {temp_root}")
    print()

    try:
        results = run_smoke(temp_root)
        print()
        print("All Agent Work Ledger MCP smoke checks passed.")
        print(f"  Case ID: {results['case_id']}")
        print(f"  Evaluation: {results['evaluation_status']}")
        if args.cleanup:
            shutil.rmtree(temp_root, ignore_errors=True)
            print(f"  Cleaned up: {temp_root}")
        else:
            print(f"  Temp files preserved at: {temp_root}")
    except Exception as error:
        print(f"\nSMOKE TEST FAILED: {error}")
        print(f"  Temp files preserved at: {temp_root}")
        sys.exit(1)


if __name__ == "__main__":
    main()
