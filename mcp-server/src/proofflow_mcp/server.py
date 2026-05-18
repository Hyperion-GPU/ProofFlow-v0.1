"""ProofFlow MCP Server – entry point and tool registration."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from proofflow_mcp.client import ProofFlowClient, ProofFlowError

_server = Server("proofflow")
_client = ProofFlowClient()
_MAX_CONCURRENT = int(os.getenv("PROOFFLOW_MCP_MAX_CONCURRENT", "5"))
_semaphore = asyncio.Semaphore(_MAX_CONCURRENT)


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
                "test_command": {
                    "type": "string",
                    "description": (
                        "Optional test command to run (e.g. 'pytest'). "
                        "Requires the backend to set PROOFFLOW_ENABLE_TEST_COMMANDS=true."
                    ),
                },
            },
            "required": ["repo_path"],
        },
    ),
    Tool(
        name="proofflow_triage_issue",
        description=(
            "Triage issue text into a ProofFlow Case. Captures the issue as an "
            "Artifact, extracts deterministic triage Claims, and makes the issue "
            "available for Proof Packet export."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Issue title."},
                "body": {"type": "string", "description": "Issue body or report text.", "default": ""},
                "source_url": {"type": "string", "description": "Optional source issue URL."},
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional issue labels.",
                    "default": [],
                },
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="proofflow_start_work_contract",
        description=(
            "Start an Agent Work Ledger Case with an explicit work contract. "
            "Use this before recording agent work events, snapshots, Evidence, or Claims."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "objective": {"type": "string", "description": "The work objective."},
                "repo_path": {"type": "string", "description": "Absolute path to the repository."},
                "allowed_scope": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Paths, modules, or workflows in scope.",
                    "default": [],
                },
                "forbidden_actions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Actions the agent must not perform.",
                    "default": [],
                },
                "required_tests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tests required before the ledger can be trusted.",
                    "default": [],
                },
                "done_criteria": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Criteria for considering the work complete.",
                    "default": [],
                },
                "evidence_requirements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Evidence required to support final claims.",
                    "default": [],
                },
                "algorithm_requirements": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Algorithm decisions required before implementation.",
                    "default": [],
                },
                "cost_budget": {
                    "type": "object",
                    "description": "Budget constraints such as token, API, GPU, CPU, or time limits.",
                    "default": {},
                },
            },
            "required": ["objective", "repo_path"],
        },
    ),
    Tool(
        name="proofflow_record_event",
        description="Record an Agent Work Ledger event as an Artifact on a ledger Case.",
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Agent Work Ledger Case ID."},
                "event_type": {"type": "string", "description": "Event type, such as plan, progress, or decision."},
                "summary": {"type": "string", "description": "Short event summary."},
                "content": {"type": "string", "description": "Detailed event content.", "default": ""},
                "metadata": {"type": "object", "description": "Optional event metadata.", "default": {}},
            },
            "required": ["case_id", "event_type", "summary"],
        },
    ),
    Tool(
        name="proofflow_record_algorithm_decision",
        description=(
            "Record an Algorithm Decision for an Agent Work Ledger Case before "
            "implementation chooses a costly or important approach."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Agent Work Ledger Case ID."},
                "summary": {"type": "string", "description": "Short decision summary."},
                "chosen_approach": {"type": "string", "description": "The selected algorithm or workflow approach."},
                "rationale": {"type": "string", "description": "Why this approach was selected."},
                "alternatives_considered": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Rejected or deferred alternatives.",
                    "default": [],
                },
                "invariants": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Algorithm invariants that must remain true.",
                    "default": [],
                },
                "forbidden_approaches": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Approaches this work must not use.",
                    "default": [],
                },
                "metadata": {"type": "object", "description": "Optional decision metadata.", "default": {}},
            },
            "required": ["case_id", "summary", "chosen_approach", "rationale"],
        },
    ),
    Tool(
        name="proofflow_record_cost_budget",
        description=(
            "Record a Cost Budget for an Agent Work Ledger Case, such as token, "
            "API, GPU, CPU, or runtime limits."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Agent Work Ledger Case ID."},
                "summary": {"type": "string", "description": "Short budget summary."},
                "budget": {
                    "type": "object",
                    "description": "Structured budget values, e.g. max_tokens, max_cost_usd, max_runtime_seconds.",
                    "default": {},
                },
                "expected_operations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Expected expensive operations.",
                    "default": [],
                },
                "limits": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Plain-language hard limits.",
                    "default": [],
                },
                "metadata": {"type": "object", "description": "Optional budget metadata.", "default": {}},
            },
            "required": ["case_id", "summary"],
        },
    ),
    Tool(
        name="proofflow_capture_snapshot",
        description="Capture a git work snapshot for an Agent Work Ledger Case.",
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Agent Work Ledger Case ID."},
                "repo_path": {"type": "string", "description": "Absolute path to the repository."},
                "phase": {
                    "type": "string",
                    "enum": ["start", "checkpoint", "final"],
                    "description": "Snapshot phase.",
                },
                "base_ref": {"type": "string", "description": "Git ref to diff against.", "default": "HEAD"},
                "include_untracked": {"type": "boolean", "description": "Include untracked files.", "default": True},
            },
            "required": ["case_id", "repo_path", "phase"],
        },
    ),
    Tool(
        name="proofflow_record_evidence",
        description="Record Evidence for an Agent Work Ledger Case.",
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Agent Work Ledger Case ID."},
                "evidence_type": {"type": "string", "description": "Evidence type, such as command_output or note."},
                "content": {"type": "string", "description": "Evidence content."},
                "source_ref": {"type": "string", "description": "Optional source reference."},
                "metadata": {"type": "object", "description": "Optional evidence metadata.", "default": {}},
            },
            "required": ["case_id", "evidence_type", "content"],
        },
    ),
    Tool(
        name="proofflow_record_claim",
        description="Record a Claim for an Agent Work Ledger Case, bound to Evidence IDs.",
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Agent Work Ledger Case ID."},
                "claim_text": {"type": "string", "description": "Claim text."},
                "severity": {
                    "type": "string",
                    "enum": ["low", "info", "medium", "high"],
                    "description": "Claim severity.",
                    "default": "info",
                },
                "evidence_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Evidence IDs supporting this Claim.",
                },
            },
            "required": ["case_id", "claim_text", "evidence_ids"],
        },
    ),
    Tool(
        name="proofflow_evaluate_contract",
        description="Evaluate an Agent Work Ledger Case against its work contract.",
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Agent Work Ledger Case ID."},
            },
            "required": ["case_id"],
        },
    ),
    Tool(
        name="proofflow_finish_work_ledger",
        description="Finish an Agent Work Ledger Case after contract evaluation and Evidence capture.",
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "Agent Work Ledger Case ID."},
                "summary": {"type": "string", "description": "Optional final summary."},
            },
            "required": ["case_id"],
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
    Tool(
        name="proofflow_decide",
        description=(
            "Create a decision on a ProofFlow Case to approve or reject a policy gate. "
            "Use this when an action is blocked with pending_decision status. "
            "Requires the case_id and action_id of the blocked action."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "case_id": {"type": "string", "description": "The Case ID."},
                "action_id": {"type": "string", "description": "The Action ID this decision applies to."},
                "decision": {
                    "type": "string",
                    "enum": ["accepted", "rejected"],
                    "description": "Accept or reject the gated action.",
                },
                "rationale": {"type": "string", "description": "Reason for the decision."},
            },
            "required": ["case_id", "action_id", "decision", "rationale"],
        },
    ),
]


# --- MCP handlers ---


@_server.list_tools()
async def list_tools() -> list[Tool]:
    return TOOLS


@_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    async with _semaphore:
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
    elif name == "proofflow_triage_issue":
        return await _handle_triage_issue(args)
    elif name == "proofflow_start_work_contract":
        return await _handle_start_work_contract(args)
    elif name == "proofflow_record_event":
        return await _handle_record_event(args)
    elif name == "proofflow_record_algorithm_decision":
        return await _handle_record_algorithm_decision(args)
    elif name == "proofflow_record_cost_budget":
        return await _handle_record_cost_budget(args)
    elif name == "proofflow_capture_snapshot":
        return await _handle_capture_snapshot(args)
    elif name == "proofflow_record_evidence":
        return await _handle_record_evidence(args)
    elif name == "proofflow_record_claim":
        return await _handle_record_claim(args)
    elif name == "proofflow_evaluate_contract":
        return await _handle_evaluate_contract(args)
    elif name == "proofflow_finish_work_ledger":
        return await _handle_finish_work_ledger(args)
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
    elif name == "proofflow_decide":
        return await _handle_decide(args)
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


async def _handle_triage_issue(args: dict[str, Any]) -> list[TextContent]:
    result = await _client.triage_issue(
        title=args["title"],
        body=args.get("body", ""),
        source_url=args.get("source_url"),
        labels=args.get("labels", []),
    )
    lines = [
        f"Issue triage complete. Case ID: {result['case_id']}",
        f"Risk level: {result['risk_level']}",
        f"Component: {result['component']}",
        f"Suggested labels: {', '.join(result['suggested_labels']) or 'none'}",
        f"Claims created: {result['claims_created']}",
        f"Evidence created: {result['evidence_created']}",
        f"Reproduction steps: {result['has_reproduction_steps']}",
        f"Expected behavior: {result['has_expected_behavior']}",
        f"Environment details: {result['has_environment_details']}",
    ]
    return _text("\n".join(lines))


async def _handle_start_work_contract(args: dict[str, Any]) -> list[TextContent]:
    result = await _client.start_work_contract(
        objective=args["objective"],
        repo_path=args["repo_path"],
        allowed_scope=args.get("allowed_scope", []),
        forbidden_actions=args.get("forbidden_actions", []),
        required_tests=args.get("required_tests", []),
        done_criteria=args.get("done_criteria", []),
        evidence_requirements=args.get("evidence_requirements", []),
        algorithm_requirements=args.get("algorithm_requirements", []),
        cost_budget=args.get("cost_budget", {}),
    )
    case = result.get("case", {})
    lines = [
        f"Agent Work Ledger started. Case ID: {result['case_id']}",
        f"Status: {result['status']}",
        f"Title: {case.get('title', args['objective'])}",
        f"Repo: {args['repo_path']}",
    ]
    return _text("\n".join(lines))


async def _handle_record_event(args: dict[str, Any]) -> list[TextContent]:
    result = await _client.record_event(
        case_id=args["case_id"],
        event_type=args["event_type"],
        summary=args["summary"],
        content=args.get("content", ""),
        metadata=args.get("metadata", {}),
    )
    return _text(
        f"Ledger event recorded.\n"
        f"Case: {result['case_id']}\n"
        f"Artifact: {result['artifact_id']}\n"
        f"Sequence: {result['sequence']}\n"
        f"Type: {result['event_type']}\n"
        f"Name: {result['name']}"
    )


async def _handle_record_algorithm_decision(args: dict[str, Any]) -> list[TextContent]:
    result = await _client.record_algorithm_decision(
        case_id=args["case_id"],
        summary=args["summary"],
        chosen_approach=args["chosen_approach"],
        rationale=args["rationale"],
        alternatives_considered=args.get("alternatives_considered", []),
        invariants=args.get("invariants", []),
        forbidden_approaches=args.get("forbidden_approaches", []),
        metadata=args.get("metadata", {}),
    )
    return _text(
        f"Ledger algorithm decision recorded.\n"
        f"Case: {result['case_id']}\n"
        f"Artifact: {result['artifact_id']}\n"
        f"Sequence: {result['sequence']}\n"
        f"Summary: {result['summary']}\n"
        f"Name: {result['name']}"
    )


async def _handle_record_cost_budget(args: dict[str, Any]) -> list[TextContent]:
    result = await _client.record_cost_budget(
        case_id=args["case_id"],
        summary=args["summary"],
        budget=args.get("budget", {}),
        expected_operations=args.get("expected_operations", []),
        limits=args.get("limits", []),
        metadata=args.get("metadata", {}),
    )
    return _text(
        f"Ledger cost budget recorded.\n"
        f"Case: {result['case_id']}\n"
        f"Artifact: {result['artifact_id']}\n"
        f"Sequence: {result['sequence']}\n"
        f"Summary: {result['summary']}\n"
        f"Name: {result['name']}"
    )


async def _handle_capture_snapshot(args: dict[str, Any]) -> list[TextContent]:
    result = await _client.capture_snapshot(
        case_id=args["case_id"],
        repo_path=args["repo_path"],
        phase=args["phase"],
        base_ref=args.get("base_ref", "HEAD"),
        include_untracked=args.get("include_untracked", True),
    )
    lines = [
        "Ledger snapshot captured.",
        f"Case: {result['case_id']}",
        f"Artifact: {result['artifact_id']}",
        f"Phase: {result['phase']}",
        f"Head SHA: {result['head_sha']}",
        f"Base ref: {result['base_ref']}",
        f"Diff SHA-256: {result['diff_sha256']}",
        f"Changed files: {len(result['changed_files'])}",
    ]
    if result["changed_files"]:
        lines.append("\nChanged files:")
        for path in result["changed_files"][:20]:
            lines.append(f"  - {path}")
    return _text("\n".join(lines))


async def _handle_record_evidence(args: dict[str, Any]) -> list[TextContent]:
    result = await _client.record_evidence(
        case_id=args["case_id"],
        evidence_type=args["evidence_type"],
        content=args["content"],
        source_ref=args.get("source_ref"),
        metadata=args.get("metadata", {}),
    )
    return _text(
        f"Ledger evidence recorded.\n"
        f"Case: {result['case_id']}\n"
        f"Artifact: {result['artifact_id']}\n"
        f"Evidence: {result['evidence_id']}\n"
        f"Type: {result['evidence_type']}"
    )


async def _handle_record_claim(args: dict[str, Any]) -> list[TextContent]:
    result = await _client.record_claim(
        case_id=args["case_id"],
        claim_text=args["claim_text"],
        severity=args.get("severity", "info"),
        evidence_ids=args["evidence_ids"],
    )
    return _text(
        f"Ledger claim recorded.\n"
        f"Case: {result['case_id']}\n"
        f"Claim: {result['claim_id']}\n"
        f"Evidence IDs: {', '.join(result['evidence_ids'])}"
    )


async def _handle_evaluate_contract(args: dict[str, Any]) -> list[TextContent]:
    result = await _client.evaluate_contract(args["case_id"])
    risk_hints = result.get("risk_hints", [])
    lines = [
        "Ledger contract evaluated.",
        f"Case: {result['case_id']}",
        f"Run: {result['run_id']}",
        f"Status: {result['status']}",
        f"Passed: {len(result['passed'])}",
        f"Failed: {len(result['failed'])}",
        f"Warnings: {len(result['warnings'])}",
        f"Missing evidence: {len(result['missing_evidence'])}",
        f"Scope violations: {len(result['scope_violations'])}",
        f"Risk hints: {len(risk_hints)}",
    ]
    for label, key in (
        ("Failed", "failed"),
        ("Warnings", "warnings"),
        ("Missing evidence", "missing_evidence"),
        ("Scope violations", "scope_violations"),
    ):
        if result[key]:
            lines.append(f"\n{label}:")
            for item in result[key][:10]:
                lines.append(f"  - {item}")
    if risk_hints:
        lines.append("\nRisk hints:")
        for hint in risk_hints[:10]:
            if not isinstance(hint, dict):
                lines.append(f"  - {hint}")
                continue
            lines.append(
                "  - "
                f"[{hint.get('severity', 'unknown')}] "
                f"{hint.get('code', 'unknown')}: {hint.get('title', 'Risk hint')}"
            )
            message = hint.get("message")
            if message:
                lines.append(f"    {message}")
    return _text("\n".join(lines))


async def _handle_finish_work_ledger(args: dict[str, Any]) -> list[TextContent]:
    result = await _client.finish_work_ledger(
        case_id=args["case_id"],
        summary=args.get("summary"),
    )
    return _text(
        f"Agent Work Ledger finished.\n"
        f"Case: {result['case_id']}\n"
        f"Status: {result['status']}\n"
        f"Finished at: {result['finished_at']}\n"
        f"Metadata: {_format_json(result['metadata'])}"
    )


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
            "Owner approval is required in the ProofFlow UI before this action can execute."
        )
    lines = [
        "Action executed successfully.",
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


async def _handle_decide(args: dict[str, Any]) -> list[TextContent]:
    # Fetch action to get policy gate metadata for binding
    case_id = args["case_id"]
    action_id = args["action_id"]
    actions = await _client.list_actions(case_id)
    gate_meta: dict[str, Any] = {}
    for action in actions:
        if action.get("id") == action_id:
            gate_meta = (action.get("metadata") or {}).get("policy_gate", {})
            break

    metadata = {
        "decision_kind": "policy_gate_owner_decision",
        "action_id": action_id,
        "policy_evaluation_id": gate_meta.get("pipeline_id", ""),
        "preview_hash": gate_meta.get("preview_hash", ""),
    }

    result = await _client.create_decision(
        case_id=case_id,
        title=f"Decision on action {action_id}",
        status=args["decision"],
        rationale=args["rationale"],
        result=args["decision"],
        metadata=metadata,
    )
    return _text(
        f"Decision created.\n"
        f"ID: {result['id']}\n"
        f"Case: {result['case_id']}\n"
        f"Status: {result['status']}\n"
        f"Rationale: {result['rationale']}"
    )


# --- Entry point ---


async def _run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await _server.run(read_stream, write_stream, _server.create_initialization_options())


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
