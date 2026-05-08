"""Generate real ProofFlow workflow output for documentation.

Runs a complete Codex-like workflow through the MCP tools and captures
all output for use in docs/codex_workflow.md and docs/examples/.

Usage:
    python scripts/generate_real_docs_output.py
"""

from __future__ import annotations

import json
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


def _sync_to_httpx_response(test_client: Any, request: httpx.Request) -> httpx.Response:
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


def main() -> None:
    tmp = tempfile.mkdtemp(prefix="proofflow-docs-gen-")
    db_path = Path(tmp) / "docs.db"
    data_dir = Path(tmp) / "pfdata"
    os.environ["PROOFFLOW_DB_PATH"] = str(db_path)
    os.environ["PROOFFLOW_DATA_DIR"] = str(data_dir)
    os.environ["PROOFFLOW_BASE_URL"] = "http://testserver"

    from fastapi.testclient import TestClient
    from proofflow.main import app
    from proofflow_mcp import server as mcp_server

    outputs: dict[str, str] = {}

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
        from proofflow_mcp.server import call_tool

        # --- Step 1: Health check ---
        print("[1/6] proofflow_health")
        result = asyncio.run(call_tool("proofflow_health", {}))
        outputs["health"] = result[0].text
        print(outputs["health"])
        print()

        # --- Step 2: Scan a project directory ---
        print("[2/6] proofflow_scan")
        project_dir = Path(tmp) / "my_project"
        project_dir.mkdir()
        (project_dir / "src").mkdir()
        (project_dir / "src" / "auth.ts").write_text(
            'import jwt from "jsonwebtoken";\n\n'
            "export function verifyToken(token: string) {\n"
            "  return jwt.verify(token, process.env.JWT_SECRET!);\n"
            "}\n",
            encoding="utf-8",
        )
        (project_dir / "src" / "utils.ts").write_text(
            "export function formatDate(d: Date): string {\n"
            '  return d.toISOString().split("T")[0];\n'
            "}\n",
            encoding="utf-8",
        )
        (project_dir / "README.md").write_text(
            "# My Project\n\nA sample TypeScript project.\n",
            encoding="utf-8",
        )
        (project_dir / "notes.txt").write_text(
            "TODO: refactor auth module\nTODO: add tests\n",
            encoding="utf-8",
        )

        result = asyncio.run(call_tool("proofflow_scan", {"folder_path": str(project_dir)}))
        outputs["scan"] = result[0].text
        print(outputs["scan"])
        print()

        # Extract case_id
        case_id = None
        for line in outputs["scan"].split("\n"):
            if "Case ID:" in line:
                case_id = line.split("Case ID:")[1].strip()
                break
        assert case_id, "Could not extract case_id"

        # --- Step 3: Suggest actions ---
        print("[3/6] proofflow_suggest")
        target_root = Path(tmp) / "organized"
        result = asyncio.run(call_tool("proofflow_suggest", {
            "case_id": case_id,
            "target_root": str(target_root),
        }))
        outputs["suggest"] = result[0].text
        print(outputs["suggest"])
        print()

        # --- Step 4: List actions and approve+execute one ---
        print("[4/6] proofflow_list_actions + approve_execute")
        result = asyncio.run(call_tool("proofflow_list_actions", {"case_id": case_id}))
        outputs["list_actions"] = result[0].text
        print(outputs["list_actions"])
        print()

        # Get first action_id from the actions list
        actions_resp = test_client.get(f"/cases/{case_id}/actions").json()
        if actions_resp:
            first_action = actions_resp[0]
            action_id = first_action["id"]
            print(f"  Executing action: {first_action['title']} ({action_id})")

            # Approve and execute (may trigger policy gate)
            result = asyncio.run(call_tool("proofflow_approve_execute", {
                "action_id": action_id,
                "confirmed_preview": True,
            }))
            outputs["approve_execute"] = result[0].text
            print(outputs["approve_execute"])
            print()

            # If policy gate triggered, resolve it
            action_after = test_client.get(f"/cases/{case_id}/actions").json()
            gated_action = [a for a in action_after if a["id"] == action_id][0]
            if gated_action["status"] == "pending_decision":
                print("  [Policy Gate triggered — resolving...]")
                gate_meta = gated_action.get("metadata", {}).get("policy_gate", {})
                result = asyncio.run(call_tool("proofflow_decide", {
                    "case_id": case_id,
                    "action_id": action_id,
                    "decision": "accepted",
                    "rationale": "Approved after reviewing the move target",
                }))
                outputs["decide"] = result[0].text
                print(outputs["decide"])
                print()

                # Re-execute
                result = asyncio.run(call_tool("proofflow_approve_execute", {
                    "action_id": action_id,
                    "confirmed_preview": True,
                }))
                outputs["re_execute"] = result[0].text
                print(outputs["re_execute"])
                print()

        # --- Step 5: AgentGuard review ---
        print("[5/6] proofflow_review")
        repo_dir = Path(tmp) / "code_repo"
        repo_dir.mkdir()
        subprocess.run(["git", "init"], cwd=str(repo_dir), capture_output=True)
        subprocess.run(["git", "config", "user.email", "dev@example.com"],
                       cwd=str(repo_dir), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Developer"],
                       cwd=str(repo_dir), capture_output=True)
        (repo_dir / "auth.py").write_text(
            "def login(username, password):\n"
            "    # TODO: add rate limiting\n"
            "    return check_credentials(username, password)\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "add", "."], cwd=str(repo_dir), capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial auth module"],
                       cwd=str(repo_dir), capture_output=True)
        # Make a change
        (repo_dir / "auth.py").write_text(
            "import hashlib\n\n"
            "def login(username, password):\n"
            "    hashed = hashlib.sha256(password.encode()).hexdigest()\n"
            "    return check_credentials(username, hashed)\n\n"
            "def logout(session_id):\n"
            "    return invalidate_session(session_id)\n",
            encoding="utf-8",
        )

        result = asyncio.run(call_tool("proofflow_review", {"repo_path": str(repo_dir)}))
        outputs["review"] = result[0].text
        print(outputs["review"])
        print()

        # --- Step 6: Export Proof Packet ---
        print("[6/6] proofflow_export_packet")
        result = asyncio.run(call_tool("proofflow_export_packet", {"case_id": case_id}))
        outputs["export_packet"] = result[0].text
        print(outputs["export_packet"])
        print()

        # Also get the raw packet content
        packet_resp = test_client.get(f"/cases/{case_id}/packet").json()
        outputs["packet_json"] = json.dumps(packet_resp, indent=2, ensure_ascii=False)

        # Get the exported markdown file path from the output
        export_resp = test_client.post(f"/reports/cases/{case_id}/export").json()
        if "path" in export_resp:
            packet_path = Path(export_resp["path"])
            if packet_path.exists():
                outputs["packet_markdown"] = packet_path.read_text(encoding="utf-8")

    # Write outputs
    output_dir = REPO_ROOT / "docs" / "examples" / "_real_output"
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (output_dir / f"{name}.txt").write_text(content, encoding="utf-8")

    print("=" * 60)
    print(f"All outputs saved to: {output_dir}")
    print(f"Temp dir: {tmp}")

    # Cleanup
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
