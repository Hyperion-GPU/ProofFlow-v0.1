"""ProofFlow MCP Demo Workflow.

Demonstrates the full audit lifecycle through MCP tools:
  Health → Scan → Suggest → List Actions → Preview → Execute → Status → Export

Uses the same in-process TestClient approach as mcp_smoke.py.

Usage:
    python scripts/demo_workflow.py [--verbose] [--cleanup]
"""

from __future__ import annotations

import argparse
import os
import shutil
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

VERBOSE = False


def banner(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def step(num: int, title: str) -> None:
    print(f"\n--- Step {num}: {title} ---\n")


def show(text: str) -> None:
    for line in text.split("\n"):
        print(f"  {line}")
    print()


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


def run_demo(temp_root: Path) -> None:
    temp_root = temp_root.resolve()
    db_path = temp_root / "demo.db"
    data_dir = temp_root / "data"
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

        import asyncio

        asyncio.run(_demo_flow(temp_root))


async def _demo_flow(temp_root: Path) -> None:
    from proofflow_mcp.server import call_tool

    # Step 1: Health check
    step(1, "Health Check")
    print("  Verifying ProofFlow backend connectivity...")
    result = await call_tool("proofflow_health", {})
    show(result[0].text)

    # Step 2: Scan files
    step(2, "Scan Files")
    inbox = temp_root / "project_files"
    inbox.mkdir(parents=True, exist_ok=True)
    (inbox / "README.md").write_text("# My Project\nA sample project.\n", encoding="utf-8")
    (inbox / "notes.txt").write_text("Meeting notes from 2026-01-15\n", encoding="utf-8")
    (inbox / "report.pdf.log").write_text("PDF conversion log\n", encoding="utf-8")
    print(f"  Created 3 test files in: {inbox}")
    print("  Scanning folder to create a Case with Artifacts...")
    result = await call_tool("proofflow_scan", {"folder_path": str(inbox)})
    show(result[0].text)

    # Extract case_id
    case_id = None
    for line in result[0].text.split("\n"):
        if "Case ID:" in line:
            case_id = line.split("Case ID:")[1].strip()
            break

    if not case_id:
        print("  ERROR: Could not extract case_id")
        return

    # Step 3: Suggest actions
    step(3, "Suggest Organization Actions")
    target = temp_root / "organized"
    print(f"  Generating suggestions to organize files into: {target}")
    result = await call_tool("proofflow_suggest", {
        "case_id": case_id,
        "target_root": str(target),
    })
    show(result[0].text)

    # Step 4: List actions
    step(4, "List Pending Actions")
    result = await call_tool("proofflow_list_actions", {"case_id": case_id})
    show(result[0].text)

    # Extract first action_id
    action_id = None
    for line in result[0].text.split("\n"):
        if "[" in line and "]" in line and "move_file" in line:
            action_id = line.split("[")[1].split("]")[0]
            break

    if action_id:
        # Step 5: Preview action (No Preview, no Action)
        step(5, "Preview Action (Phase 1)")
        print("  Calling approve_execute WITHOUT confirmed_preview...")
        print("  This shows the preview but does NOT move any files.")
        result = await call_tool("proofflow_approve_execute", {"action_id": action_id})
        show(result[0].text)

        # Step 6: Execute action
        step(6, "Execute Action (Phase 2)")
        print("  Now calling with confirmed_preview=true to actually move the file...")
        result = await call_tool("proofflow_approve_execute", {
            "action_id": action_id,
            "confirmed_preview": True,
        })
        show(result[0].text)
    else:
        print("  No move_file actions found, skipping execute demo.")

    # Step 7: Case status
    step(7, "Case Status")
    result = await call_tool("proofflow_status", {"case_id": case_id})
    show(result[0].text)

    # Step 8: Export proof packet
    step(8, "Export Proof Packet")
    print("  Generating shareable audit report...")
    result = await call_tool("proofflow_export_packet", {"case_id": case_id})
    text = result[0].text
    # Show first 30 lines of the packet
    lines = text.split("\n")
    show("\n".join(lines[:30]))
    if len(lines) > 30:
        print(f"  ... ({len(lines) - 30} more lines)")


def main() -> None:
    global VERBOSE
    parser = argparse.ArgumentParser(description="ProofFlow MCP Demo Workflow")
    parser.add_argument("--verbose", action="store_true", help="Show full JSON responses")
    parser.add_argument("--cleanup", action="store_true", help="Remove temp files on completion")
    args = parser.parse_args()
    VERBOSE = args.verbose

    temp_root = Path(tempfile.mkdtemp(prefix="proofflow-demo-"))

    banner("ProofFlow MCP Demo Workflow")
    print(f"  This demo shows the full audit lifecycle through MCP tools.")
    print(f"  Temp directory: {temp_root}")

    try:
        run_demo(temp_root)
        banner("Demo Complete")
        if args.cleanup:
            shutil.rmtree(temp_root, ignore_errors=True)
            print(f"  Cleaned up: {temp_root}")
        else:
            print(f"  Temp files preserved at: {temp_root}")
    except Exception as e:
        print(f"\n  DEMO FAILED: {e}")
        print(f"  Temp files at: {temp_root}")
        sys.exit(1)


if __name__ == "__main__":
    main()
