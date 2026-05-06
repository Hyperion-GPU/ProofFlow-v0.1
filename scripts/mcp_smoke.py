"""End-to-end smoke test for ProofFlow MCP Server.

Starts the ProofFlow backend in-process (TestClient), then exercises
MCP tool handlers against the real API to verify the full chain.

Usage:
    python scripts/mcp_smoke.py [--cleanup]
"""

from __future__ import annotations

import argparse
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
    db_path = temp_root / "mcp-smoke.db"
    data_dir = temp_root / "data"
    os.environ["PROOFFLOW_DB_PATH"] = str(db_path)
    os.environ["PROOFFLOW_DATA_DIR"] = str(data_dir)
    # Point MCP client at the test server
    os.environ["PROOFFLOW_BASE_URL"] = "http://testserver"

    from fastapi.testclient import TestClient
    from proofflow.main import app

    from proofflow_mcp import server as mcp_server

    results: dict[str, Any] = {}

    with TestClient(app) as test_client:
        # Patch the MCP client to use the TestClient's transport
        patched_http = httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda req: _sync_to_httpx_response(test_client, req)
            ),
            base_url="http://testserver",
        )
        mcp_server._client._http = patched_http
        mcp_server._client._base_url = "http://testserver"

        import asyncio

        results["health"] = asyncio.run(_test_health())
        results["scan"] = asyncio.run(_test_scan(temp_root))
        results["review"] = asyncio.run(_test_review(temp_root))
        results["search"] = asyncio.run(_test_search())
        results["list_cases"] = asyncio.run(_test_list_cases())

    return results


def _sync_to_httpx_response(
    test_client: Any, request: httpx.Request
) -> httpx.Response:
    """Convert an httpx request to a TestClient call and return httpx.Response."""
    method = request.method.lower()
    url = str(request.url)
    parsed = urlparse(url)
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


async def _test_health() -> dict[str, Any]:
    from proofflow_mcp.server import call_tool

    result = await call_tool("proofflow_health", {})
    text = result[0].text
    assert "ProofFlow is running" in text, f"Health check failed: {text}"
    print("  [PASS] proofflow_health")
    return {"passed": True}


async def _test_scan(temp_root: Path) -> dict[str, Any]:
    from proofflow_mcp.server import call_tool

    # Create test files
    inbox = temp_root / "scan_test"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "readme.md").write_text("# Test\nSome content\n", encoding="utf-8")
    (inbox / "data.log").write_text("2026-01-01 INFO started\n", encoding="utf-8")

    # Scan
    result = await call_tool("proofflow_scan", {"folder_path": str(inbox)})
    text = result[0].text
    assert "Scan complete" in text, f"Scan failed: {text}"
    assert "Files seen: 2" in text, f"Expected 2 files: {text}"

    # Extract case_id from output
    case_id = None
    for line in text.split("\n"):
        if "Case ID:" in line:
            case_id = line.split("Case ID:")[1].strip()
            break
    assert case_id, f"Could not extract case_id from: {text}"

    # Suggest actions
    target = temp_root / "organized"
    result = await call_tool(
        "proofflow_suggest",
        {"case_id": case_id, "target_root": str(target)},
    )
    text = result[0].text
    assert "Suggestions generated" in text, f"Suggest failed: {text}"

    # List actions
    result = await call_tool("proofflow_list_actions", {"case_id": case_id})
    text = result[0].text
    assert "Actions for case" in text, f"List actions failed: {text}"

    # Status
    result = await call_tool("proofflow_status", {"case_id": case_id})
    text = result[0].text
    assert "Kind:" in text and "Status:" in text, f"Status failed: {text}"

    # Export packet
    result = await call_tool("proofflow_export_packet", {"case_id": case_id})
    text = result[0].text
    assert "Proof Packet exported" in text, f"Export failed: {text}"

    print("  [PASS] proofflow_scan + suggest + list_actions + status + export_packet")
    return {"passed": True, "case_id": case_id}


async def _test_review(temp_root: Path) -> dict[str, Any]:
    from proofflow_mcp.server import call_tool

    if shutil.which("git") is None:
        print("  [SKIP] proofflow_review (git not found)")
        return {"skipped": True}

    # Create a temp git repo with changes
    repo = temp_root / "review_repo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=str(repo), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(repo),
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(repo),
        capture_output=True,
    )
    (repo / "main.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(repo), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=str(repo),
        capture_output=True,
    )
    (repo / "main.py").write_text("x = 2\n", encoding="utf-8")

    result = await call_tool("proofflow_review", {"repo_path": str(repo)})
    text = result[0].text
    assert "Code review complete" in text, f"Review failed: {text}"
    assert "main.py" in text, f"main.py not in review: {text}"

    print("  [PASS] proofflow_review")
    return {"passed": True}


async def _test_search() -> dict[str, Any]:
    from proofflow_mcp.server import call_tool

    result = await call_tool("proofflow_search", {"query": "content"})
    text = result[0].text
    # May or may not find results depending on scan indexing
    assert "results" in text.lower() or "no results" in text.lower(), f"Search unexpected: {text}"
    print("  [PASS] proofflow_search")
    return {"passed": True}


async def _test_list_cases() -> dict[str, Any]:
    from proofflow_mcp.server import call_tool

    result = await call_tool("proofflow_list_cases", {})
    text = result[0].text
    assert "Cases" in text or "No cases" in text, f"List cases unexpected: {text}"
    print("  [PASS] proofflow_list_cases")
    return {"passed": True}


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP Server end-to-end smoke test")
    parser.add_argument("--cleanup", action="store_true", help="Remove temp files on success")
    args = parser.parse_args()

    temp_root = Path(tempfile.mkdtemp(prefix="proofflow-mcp-smoke-"))
    print(f"MCP Smoke Test")
    print(f"  temp_root: {temp_root}")
    print()

    try:
        results = run_smoke(temp_root)
        print()
        print("All MCP smoke checks passed.")
        if args.cleanup:
            shutil.rmtree(temp_root, ignore_errors=True)
            print(f"  Cleaned up: {temp_root}")
        else:
            print(f"  Temp files preserved at: {temp_root}")
    except Exception as e:
        print(f"\nSMOKE TEST FAILED: {e}")
        print(f"  Temp files preserved at: {temp_root}")
        sys.exit(1)


if __name__ == "__main__":
    main()
