"""ProofFlow MCP Server – entry point and tool registration."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from proofflow_mcp.client import ProofFlowClient, ProofFlowError

_server = Server("proofflow")
_client = ProofFlowClient()


def _text(content: str) -> list[TextContent]:
    return [TextContent(type="text", text=content)]


def _format_json(data: Any, indent: int = 2) -> str:
    return json.dumps(data, indent=indent, ensure_ascii=False, default=str)


# --- Tool definitions ---

TOOLS: list[Tool] = [
    Tool(
        name="proofflow_health",
        description=(
            "Check if the ProofFlow backend is running and return version info. "
            "Call this first to verify connectivity before using other tools."
        ),
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="proofflow_scan",
        description=(
            "Scan a local folder to create a ProofFlow Case with file Artifacts. "
            "Indexes files with SHA-256 hashes and extracts text for full-text search. "
            "Use this to audit or organize files in a directory."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "folder_path": {"type": "string", "description": "Absolute path to the folder to scan."},
                "recursive": {"type": "boolean", "description": "Scan subdirectories.", "default": True},
                "max_files": {"type": "integer", "description": "Maximum files to index.", "default": 500},
            },
            "required": ["folder_path"],
        },
    ),
    Tool(
        name="proofflow_suggest",
        description=(
            "Generate file cleanup/organization suggestions for a scanned Case. "
            "Requires a case_id from a prior proofflow_scan and a target_root directory "
            "where organized files should be moved to."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Case ID from a prior scan."},
                "target_root": {"type": "string", "description": "Absolute path to the target organization root."},
            },
            "required": ["case_id", "target_root"],
        },
    ),
    Tool(
        name="proofflow_review",
        description=(
            "Run an AgentGuard code review on a local git repository. "
            "Analyzes git diff, generates evidence-backed claims about risk, "
            "and creates a code_review Case. Use after making code changes to audit them."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "Absolute path to the git repository."},
                "base_ref": {"type": "string", "description": "Git ref to diff against.", "default": "HEAD"},
                "include_untracked": {"type": "boolean", "description": "Include untracked files.", "default": True},
                "test_command": {"type": "string", "description": "Optional test command to run (e.g. 'pytest')."},
            },
            "required": ["repo_path"],
        },
    ),
    Tool(
        name="proofflow_status",
        description=(
            "Get the full status of a ProofFlow Case including artifacts, claims, "
            "actions, decisions, and policy observations. Use to check progress on a workflow."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "The Case ID to inspect."},
            },
            "required": ["case_id"],
        },
    ),
    Tool(
        name="proofflow_approve_execute",
        description=(
            "Approve and execute a pending ProofFlow action (e.g. move_file, rename_file, mkdir_dir). "
            "IMPORTANT: First call WITHOUT confirmed_preview to see the action preview. "
            "Then call again WITH confirmed_preview=true after the user has reviewed the paths. "
            "This enforces 'No Preview, no Action'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action_id": {"type": "string", "description": "The Action ID to approve and execute."},
                "confirmed_preview": {
                    "type": "boolean",
                    "description": "Set to true ONLY after the user has seen and confirmed the action preview.",
                    "default": False,
                },
            },
            "required": ["action_id"],
        },
    ),
    Tool(
        name="proofflow_export_packet",
        description=(
            "Export a ProofFlow Case as a Proof Packet (markdown report). "
            "Contains summary, artifacts, claims, evidence, actions, and decisions. "
            "Use to generate a shareable audit report."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "The Case ID to export."},
            },
            "required": ["case_id"],
        },
    ),
    Tool(
        name="proofflow_search",
        description=(
            "Full-text search across all indexed artifact text in ProofFlow. "
            "Returns matching snippets with file paths and scores."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query string."},
                "limit": {"type": "integer", "description": "Max results to return.", "default": 10},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="proofflow_list_cases",
        description="List all ProofFlow Cases with their status, kind, and timestamps.",
        inputSchema={"type": "object", "properties": {}, "required": []},
    ),
    Tool(
        name="proofflow_list_actions",
        description="List all actions for a given ProofFlow Case.",
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "The Case ID."},
            },
            "required": ["case_id"],
        },
    ),
    Tool(
        name="proofflow_undo",
        description=(
            "Undo a previously executed ProofFlow action. "
            "Only works on actions with status 'executed' that have undo metadata."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "action_id": {"type": "string", "description": "The Action ID to undo."},
            },
            "required": ["action_id"],
        },
    ),
]


# --- MCP handlers ---


@_server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        return await _dispatch(name, arguments)
    except ProofFlowError as e:
        return _text(f"Error: {e}")


async def _dispatch(name: str, args: dict[str, Any]) -> list[TextContent]:
    if name == "proofflow_health":
        return await _handle_health()
    elif name == "proofflow_scan":
        return await _handle_scan(args)
    elif name == "proofflow_suggest":
        return await _handle_suggest(args)
    elif name == "proofflow_review":
        return await _handle_review(args)
    elif name == "proofflow_status":
        return await _handle_status(args)
    elif name == "proofflow_approve_execute":
        return await _handle_approve_execute(args)
    elif name == "proofflow_export_packet":
        return await _handle_export_packet(args)
    elif name == "proofflow_search":
        return await _handle_search(args)
    elif name == "proofflow_list_cases":
        return await _handle_list_cases()
    elif name == "proofflow_list_actions":
        return await _handle_list_actions(args)
    elif name == "proofflow_undo":
        return await _handle_undo(args)
    else:
        return _text(f"Unknown tool: {name}")


# --- Tool handlers ---


async def _handle_health() -> list[TextContent]:
    data = await _client.health()
    return _text(
        f"ProofFlow is running.\n"
        f"Version: {data.get('version', 'unknown')}\n"
        f"Release: {data.get('release_name', 'unknown')}\n"
        f"Stage: {data.get('release_stage', 'unknown')}"
    )


async def _handle_scan(args: dict[str, Any]) -> list[TextContent]:
    result = await _client.scan(
        folder_path=args["folder_path"],
        recursive=args.get("recursive", True),
        max_files=args.get("max_files", 500),
    )
    lines = [
        f"Scan complete. Case ID: {result['case_id']}",
        f"Files seen: {result['files_seen']}",
        f"Artifacts created: {result['artifacts_created']}",
        f"Text chunks indexed: {result['text_chunks_created']}",
        f"Skipped: {result['skipped']}",
    ]
    if result.get("skipped_items"):
        lines.append("\nSkipped items:")
        for item in result["skipped_items"][:10]:
            lines.append(f"  - {item['path']}: {item['reason']}")
    return _text("\n".join(lines))


async def _handle_suggest(args: dict[str, Any]) -> list[TextContent]:
    result = await _client.suggest_actions(
        case_id=args["case_id"],
        target_root=args["target_root"],
    )
    lines = [
        f"Suggestions generated for Case: {result['case_id']}",
        f"Target root: {result['target_root']}",
        f"Actions created: {result['actions_created']}",
        f"Skipped: {result['skipped']}",
    ]
    if result.get("actions"):
        lines.append("\nSuggested actions:")
        for action in result["actions"]:
            preview = action.get("preview", {})
            if action["kind"] in ("move_file", "rename_file"):
                lines.append(
                    f"  [{action['id']}] {action['kind']}: "
                    f"{preview.get('from_path', '?')} -> {preview.get('to_path', '?')}"
                )
            elif action["kind"] == "mkdir_dir":
                lines.append(
                    f"  [{action['id']}] mkdir: {preview.get('dir_path', '?')}"
                )
            else:
                lines.append(f"  [{action['id']}] {action['kind']}: {action['title']}")
    return _text("\n".join(lines))


async def _handle_review(args: dict[str, Any]) -> list[TextContent]:
    result = await _client.review(
        repo_path=args["repo_path"],
        base_ref=args.get("base_ref", "HEAD"),
        include_untracked=args.get("include_untracked", True),
        test_command=args.get("test_command"),
    )
    lines = [
        f"Code review complete. Case ID: {result['case_id']}",
        f"Risk level: {result['risk_level']}",
        f"Changed files: {len(result['changed_files'])}",
        f"Claims created: {result['claims_created']}",
        f"Evidence created: {result['evidence_created']}",
    ]
    if result["changed_files"]:
        lines.append("\nChanged files:")
        for f in result["changed_files"][:20]:
            lines.append(f"  - {f}")
    return _text("\n".join(lines))


async def _handle_status(args: dict[str, Any]) -> list[TextContent]:
    packet = await _client.get_case_packet(args["case_id"])
    case = packet["case"]
    lines = [
        f"Case: {case['title']}",
        f"ID: {case['id']}",
        f"Kind: {case['kind']} | Status: {case['status']}",
        f"Risk level: {packet['risk_level']}",
        f"Artifacts: {len(packet['artifacts'])}",
        f"Claims: {len(packet['claims'])}",
        f"Actions: {len(packet['actions'])}",
        f"Decisions: {len(packet['decisions'])}",
    ]
    if packet["actions"]:
        lines.append("\nActions:")
        for a in packet["actions"]:
            lines.append(f"  [{a['id']}] {a['kind']} — {a['status']}: {a['title']}")
    if packet["claims"]:
        lines.append("\nClaims:")
        for c in packet["claims"][:10]:
            lines.append(f"  [{c['severity']}] {c['claim_text']}")
    return _text("\n".join(lines))


async def _handle_approve_execute(args: dict[str, Any]) -> list[TextContent]:
    action_id = args["action_id"]
    confirmed = args.get("confirmed_preview", False)

    # Step 1: Approve (safe — does not move files, only changes status)
    try:
        action_data = await _client.approve_action(action_id)
    except ProofFlowError as e:
        if e.status_code == 400 and "approved" in str(e).lower():
            # Already approved — still need to show preview if not confirmed
            if not confirmed:
                return _text(
                    f"Action {action_id} is already approved but not yet executed.\n"
                    f"Call again with confirmed_preview=true to execute."
                )
            # If confirmed, proceed to execute below
            action_data = None
        else:
            raise

    # If not confirmed, show preview and stop — enforce "No Preview, no Action"
    if not confirmed:
        preview = action_data.get("preview", {}) if action_data else {}
        kind = action_data.get("kind", "unknown") if action_data else "unknown"
        lines = [
            "Action preview (NOT yet executed):",
            f"  ID: {action_id}",
            f"  Kind: {kind}",
            f"  Title: {action_data.get('title', '?')}",
            f"  Reason: {action_data.get('reason', '?')}",
        ]
        if kind in ("move_file", "rename_file"):
            lines.append(f"  From: {preview.get('from_path', '?')}")
            lines.append(f"  To:   {preview.get('to_path', '?')}")
        elif kind == "mkdir_dir":
            lines.append(f"  Directory: {preview.get('dir_path', '?')}")
        lines.append("")
        lines.append(
            "Review the paths above. To execute, call proofflow_approve_execute "
            "again with the same action_id and confirmed_preview=true."
        )
        return _text("\n".join(lines))

    # Step 2: Execute (destructive — moves/renames files on disk)
    result = await _client.execute_action(action_id)
    status = result.get("status", "unknown")
    if status == "pending_decision":
        return _text(
            f"Action {action_id} is blocked by a policy gate (pending_decision).\n"
            f"Owner approval is required in the ProofFlow UI before this action can execute."
        )
    lines = [
        f"Action executed successfully.",
        f"ID: {result['id']}",
        f"Kind: {result['kind']}",
        f"Status: {result['status']}",
        f"Title: {result['title']}",
    ]
    if result.get("result"):
        lines.append(f"Result: {_format_json(result['result'])}")
    return _text("\n".join(lines))


async def _handle_export_packet(args: dict[str, Any]) -> list[TextContent]:
    result = await _client.export_report(args["case_id"])
    content = result.get("content", "")
    # Truncate very long packets for MCP response
    if len(content) > 8000:
        content = content[:8000] + "\n\n... [truncated, full packet saved to disk]"
    lines = [
        f"Proof Packet exported for Case: {result['case_id']}",
        f"File: {result.get('filename', 'unknown')}",
        f"Path: {result.get('path', 'unknown')}",
        "",
        content,
    ]
    return _text("\n".join(lines))


async def _handle_search(args: dict[str, Any]) -> list[TextContent]:
    result = await _client.search(
        query=args["query"],
        limit=args.get("limit", 10),
    )
    results = result.get("results", [])
    if not results:
        return _text(f"No results found for: {args['query']}")
    lines = [f"Search results for '{result['query']}' ({len(results)} matches):"]
    for r in results:
        lines.append(f"\n  [{r['name']}] (score: {r['score']:.2f})")
        if r.get("path"):
            lines.append(f"    Path: {r['path']}")
        lines.append(f"    {r['snippet'][:200]}")
    return _text("\n".join(lines))


async def _handle_list_cases() -> list[TextContent]:
    cases = await _client.list_cases()
    if not cases:
        return _text("No cases found.")
    lines = [f"ProofFlow Cases ({len(cases)} total):"]
    for c in cases:
        lines.append(
            f"  [{c['id']}] {c['kind']} | {c['status']} — {c['title']}"
        )
    return _text("\n".join(lines))


async def _handle_list_actions(args: dict[str, Any]) -> list[TextContent]:
    actions = await _client.list_actions(args["case_id"])
    if not actions:
        return _text(f"No actions found for case {args['case_id']}.")
    lines = [f"Actions for case {args['case_id']} ({len(actions)} total):"]
    for a in actions:
        preview = a.get("preview", {})
        detail = ""
        if a["kind"] in ("move_file", "rename_file"):
            detail = f" ({preview.get('from_path', '?')} -> {preview.get('to_path', '?')})"
        elif a["kind"] == "mkdir_dir":
            detail = f" ({preview.get('dir_path', '?')})"
        lines.append(f"  [{a['id']}] {a['kind']} — {a['status']}: {a['title']}{detail}")
    return _text("\n".join(lines))


async def _handle_undo(args: dict[str, Any]) -> list[TextContent]:
    result = await _client.undo_action(args["action_id"])
    return _text(
        f"Action undone successfully.\n"
        f"ID: {result['id']}\n"
        f"Kind: {result['kind']}\n"
        f"Status: {result['status']}\n"
        f"Title: {result['title']}"
    )


# --- Entry point ---


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await _server.run(read_stream, write_stream, _server.create_initialization_options())


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
