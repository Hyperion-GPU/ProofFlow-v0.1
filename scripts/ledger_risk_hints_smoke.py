"""Smoke test Ledger Risk Hints through the MCP tool path.

This synthetic dogfood scenario is intentionally domain-neutral. It models a
data conversion pipeline where the contract asks to preserve source mapping and
lineage, but the recorded algorithm route regenerates derived records and the
test evidence reports expensive usage.

Usage:
    python scripts/ledger_risk_hints_smoke.py [--cleanup]
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
    db_path = temp_root / "ledger-risk-hints-smoke.db"
    data_dir = temp_root / "data"
    repo = _init_repo(temp_root / "repo")

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
            "objective": "Preserve source mapping and lineage in a data conversion pipeline",
            "repo_path": str(repo),
            "allowed_scope": ["pipeline.py"],
            "required_tests": ["python -m pytest synthetic"],
            "done_criteria": ["Converted rows retain source lineage"],
            "evidence_requirements": [
                "git_diff",
                "test_output",
                "algorithm_decision",
                "cost_budget",
            ],
            "algorithm_requirements": ["preserve source mapping and lineage"],
            "cost_budget": {"max_api_calls": 0, "max_gpu_jobs": 0},
        },
    )
    case_id = _extract_value(start, "Case ID")
    print(f"  [PASS] proofflow_start_work_contract -> {case_id}")

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
    print("  [PASS] proofflow_capture_snapshot start")

    decision = await _call(
        "proofflow_record_algorithm_decision",
        {
            "case_id": case_id,
            "summary": "Regenerate derived records",
            "chosen_approach": "Regenerate derived records with a new API call.",
            "rationale": "This is simpler than preserving source mapping through the transform.",
            "alternatives_considered": ["Carry source IDs through a local mapping table"],
            "invariants": ["Output schema remains stable"],
            "forbidden_approaches": ["regenerate derived records"],
        },
    )
    _assert_contains(decision, "Ledger algorithm decision recorded.")
    print("  [PASS] proofflow_record_algorithm_decision")

    budget = await _call(
        "proofflow_record_cost_budget",
        {
            "case_id": case_id,
            "summary": "Local-only conversion budget",
            "budget": {"max_api_calls": 0, "max_gpu_jobs": 0},
            "expected_operations": ["local mapping transform"],
            "limits": ["Do not call APIs", "Do not run GPU jobs"],
        },
    )
    _assert_contains(budget, "Ledger cost budget recorded.")
    print("  [PASS] proofflow_record_cost_budget")

    (repo / "pipeline.py").write_text(
        "def convert(rows):\n"
        "    return [{'derived': row['value'] * 2} for row in rows]\n",
        encoding="utf-8",
    )
    event = await _call(
        "proofflow_record_event",
        {
            "case_id": case_id,
            "event_type": "implementation",
            "summary": "Implemented conversion output path",
            "content": "Synthetic pipeline now emits derived rows.",
            "metadata": {"file": "pipeline.py"},
        },
    )
    _assert_contains(event, "Ledger event recorded.")
    print("  [PASS] proofflow_record_event")

    evidence = await _call(
        "proofflow_record_evidence",
        {
            "case_id": case_id,
            "evidence_type": "test_output",
            "content": "COMMAND: python -m pytest synthetic\nRETURN_CODE: 0\n1 passed\n",
            "source_ref": "ledger_risk_hints_smoke.py",
            "metadata": {
                "command": "python -m pytest synthetic",
                "usage": {"api_calls": 3, "gpu_jobs": 1},
            },
        },
    )
    evidence_id = _extract_value(evidence, "Evidence")
    print(f"  [PASS] proofflow_record_evidence -> {evidence_id}")

    claim = await _call(
        "proofflow_record_claim",
        {
            "case_id": case_id,
            "claim_text": "Synthetic conversion tests passed.",
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
    _assert_contains(final_snapshot, "pipeline.py")
    print("  [PASS] proofflow_capture_snapshot final")

    evaluation = await _call("proofflow_evaluate_contract", {"case_id": case_id})
    _assert_contains(evaluation, "Status: ready_for_review")
    _assert_contains(evaluation, "Risk hints:")
    for code in (
        "forbidden_algorithm_mentioned",
        "regeneration_over_mapping",
        "cost_budget_possible_overrun",
        "test_proves_output_not_method",
    ):
        _assert_contains(evaluation, code)
    print("  [PASS] proofflow_evaluate_contract -> ready_for_review with risk hints")

    packet = await _call("proofflow_export_packet", {"case_id": case_id})
    _assert_contains(packet, "Proof Packet exported")
    _assert_contains(packet, "Risk Hints")
    _assert_contains(packet, "regeneration_over_mapping")
    _assert_contains(packet, "cost_budget_possible_overrun")
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
    _git(repo, "config", "user.email", "ledger-risk-hints@example.test")
    _git(repo, "config", "user.name", "Ledger Risk Hints")
    (repo / "pipeline.py").write_text(
        "def convert(rows):\n"
        "    return [{'source_id': row['id'], 'derived': row['value'] * 2} for row in rows]\n",
        encoding="utf-8",
    )
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
    parser = argparse.ArgumentParser(description="Ledger Risk Hints smoke test")
    parser.add_argument("--cleanup", action="store_true", help="Remove temp files on success")
    args = parser.parse_args()

    temp_root = Path(tempfile.mkdtemp(prefix="proofflow-ledger-risk-hints-smoke-"))
    print("Ledger Risk Hints Smoke Test")
    print(f"  temp_root: {temp_root}")
    print()

    try:
        results = run_smoke(temp_root)
        print()
        print("All Ledger Risk Hints smoke checks passed.")
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
