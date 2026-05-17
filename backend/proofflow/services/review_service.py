from dataclasses import dataclass
from pathlib import Path
from typing import Any

import hashlib
import json
import os
import re
import shlex
import subprocess

from proofflow.config import test_commands_enabled
from proofflow.db import connect, new_uuid, utc_now_iso
from proofflow.models.schemas import (
    AgentGuardArtifactRef,
    AgentGuardReviewRequest,
    AgentGuardReviewResponse,
)
from proofflow.services.git_service import (
    ChangedFile,
    GitSnapshot,
    UntrackedFilePolicyNote,
    inspect_working_tree,
)
from proofflow.services.json_utils import dumps_metadata

TEXT_CHUNK_LINES = 200
SEVERITY_ORDER = {"low": 0, "info": 1, "medium": 2, "high": 3}


class ReviewServiceError(ValueError):
    """Raised when AgentGuard cannot safely complete a deterministic review."""


@dataclass(frozen=True)
class TestCommandResult:
    command: str
    args: list[str]
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    started_at: str
    finished_at: str


@dataclass(frozen=True)
class ClaimSpec:
    severity: str
    text: str
    evidence_type: str
    evidence_content: str
    source_ref: str | None


@dataclass(frozen=True)
class ArtifactRecord:
    id: str
    kind: str
    name: str


@dataclass(frozen=True)
class JsonReadResult:
    data: Any
    error: str | None = None


def review_repository(payload: AgentGuardReviewRequest) -> AgentGuardReviewResponse:
    if payload.test_command is not None and payload.test_command.strip():
        if not test_commands_enabled():
            raise ReviewServiceError(
                "AgentGuard test_command execution is disabled. "
                "Set PROOFFLOW_ENABLE_TEST_COMMANDS=true to allow local test commands."
            )
    review_started_at = utc_now_iso()
    snapshot = inspect_working_tree(
        payload.repo_path,
        payload.base_ref,
        payload.include_untracked,
    )
    test_result = _run_test_command(snapshot.repo_root, payload.test_command)
    claim_specs = _build_claim_specs(snapshot, test_result)
    risk_level = _risk_level(snapshot.changed_files, claim_specs, test_result)

    case_id = new_uuid()
    run_id = new_uuid()
    with connect() as connection:
        _insert_case(connection, case_id, snapshot, payload, risk_level)
        _insert_run(connection, run_id, case_id, review_started_at, test_result, risk_level)
        diff_artifact = _insert_text_artifact(
            connection=connection,
            case_id=case_id,
            kind="git_diff",
            name="git-diff.patch",
            content=snapshot.diff_text or "No diff content captured.",
            role="primary",
            metadata={
                "source": "agentguard_review",
                "repo_path": str(snapshot.repo_root),
                "base_ref": payload.base_ref,
                "changed_files": _changed_file_metadata(snapshot.changed_files),
                "diff_line_count": len(snapshot.diff_text.splitlines()),
                "untracked_policy_notes": _untracked_policy_note_metadata(
                    snapshot.untracked_policy_notes
                ),
            },
        )

        test_artifact: ArtifactRecord | None = None
        if test_result is not None:
            test_artifact = _insert_text_artifact(
                connection=connection,
                case_id=case_id,
                kind="test_output",
                name="test-output.txt",
                content=_format_test_output(test_result),
                role="supporting",
                metadata={
                    "source": "agentguard_review",
                    "command": test_result.command,
                    "args": test_result.args,
                    "returncode": test_result.returncode,
                    "timed_out": test_result.timed_out,
                },
            )

        claims_created, evidence_created = _insert_claims_and_evidence(
            connection,
            case_id,
            run_id,
            claim_specs,
            diff_artifact,
            test_artifact,
        )
        connection.commit()

    artifact_refs = [AgentGuardArtifactRef(id=diff_artifact.id, kind="git_diff", name=diff_artifact.name)]
    if test_artifact is not None:
        artifact_refs.append(
            AgentGuardArtifactRef(id=test_artifact.id, kind="test_output", name=test_artifact.name)
        )

    return AgentGuardReviewResponse(
        case_id=case_id,
        run_id=run_id,
        risk_level=risk_level,
        changed_files=[changed_file.path for changed_file in snapshot.changed_files],
        claims_created=claims_created,
        evidence_created=evidence_created,
        artifacts=artifact_refs,
    )


def _insert_case(
    connection: Any,
    case_id: str,
    snapshot: GitSnapshot,
    payload: AgentGuardReviewRequest,
    risk_level: str,
) -> None:
    now = utc_now_iso()
    connection.execute(
        """
        INSERT INTO cases (
            id, title, case_type, status, summary, metadata_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            case_id,
            f"Code review: {snapshot.repo_root.name}",
            "code_review",
            "open",
            f"AgentGuard review for {snapshot.repo_root}",
            dumps_metadata(
                {
                    "repo_path": str(snapshot.repo_root),
                    "base_ref": payload.base_ref,
                    "include_untracked": payload.include_untracked,
                    "risk_level": risk_level,
                    "changed_file_count": len(snapshot.changed_files),
                    "untracked_policy_notes": _untracked_policy_note_metadata(
                        snapshot.untracked_policy_notes
                    ),
                }
            ),
            now,
            now,
        ),
    )


def _insert_run(
    connection: Any,
    run_id: str,
    case_id: str,
    started_at: str,
    test_result: TestCommandResult | None,
    risk_level: str,
) -> None:
    finished_at = utc_now_iso()
    test_status = _test_status(test_result)
    status = "failed" if test_status in {"failed", "timeout"} else "completed"
    connection.execute(
        """
        INSERT INTO runs (
            id, case_id, run_type, status, started_at, finished_at,
            metadata_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            case_id,
            "agentguard_review",
            status,
            started_at,
            finished_at,
            dumps_metadata(
                {
                    "risk_level": risk_level,
                    "test_status": test_status,
                    "test_command": test_result.command if test_result else None,
                    "test_returncode": test_result.returncode if test_result else None,
                    "test_timed_out": test_result.timed_out if test_result else False,
                }
            ),
            started_at,
            finished_at,
        ),
    )


def _insert_text_artifact(
    *,
    connection: Any,
    case_id: str,
    kind: str,
    name: str,
    content: str,
    role: str,
    metadata: dict[str, Any],
) -> ArtifactRecord:
    now = utc_now_iso()
    artifact_id = new_uuid()
    encoded = content.encode("utf-8")
    connection.execute(
        """
        INSERT INTO artifacts (
            id, artifact_type, uri, name, mime_type, sha256, size_bytes,
            metadata_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_id,
            kind,
            f"agentguard://{case_id}/{name}",
            name,
            "text/plain",
            hashlib.sha256(encoded).hexdigest(),
            len(encoded),
            dumps_metadata(metadata),
            now,
            now,
        ),
    )
    connection.execute(
        """
        INSERT INTO case_artifacts (
            case_id, artifact_id, role, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (case_id, artifact_id, role, now, now),
    )
    _insert_text_chunks(connection, artifact_id, content)
    return ArtifactRecord(id=artifact_id, kind=kind, name=name)


def _insert_text_chunks(connection: Any, artifact_id: str, content: str) -> None:
    lines = content.splitlines() or [""]
    for chunk_index, start in enumerate(range(0, len(lines), TEXT_CHUNK_LINES)):
        now = utc_now_iso()
        chunk_lines = lines[start : start + TEXT_CHUNK_LINES]
        chunk_content = "\n".join(chunk_lines)
        cursor = connection.execute(
            """
            INSERT INTO artifact_text_chunks (
                id, artifact_id, chunk_index, content, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_uuid(),
                artifact_id,
                chunk_index,
                chunk_content,
                dumps_metadata(
                    {
                        "start_line": start + 1,
                        "end_line": start + len(chunk_lines),
                        "source": "agentguard_review",
                    }
                ),
                now,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO artifact_text_fts(rowid, content, artifact_id, chunk_index)
            VALUES (?, ?, ?, ?)
            """,
            (cursor.lastrowid, chunk_content, artifact_id, chunk_index),
        )


def _insert_claims_and_evidence(
    connection: Any,
    case_id: str,
    run_id: str,
    claims: list[ClaimSpec],
    diff_artifact: ArtifactRecord,
    test_artifact: ArtifactRecord | None,
) -> tuple[int, int]:
    claims_created = 0
    evidence_created = 0
    for claim in claims:
        now = utc_now_iso()
        claim_id = new_uuid()
        artifact = test_artifact if claim.evidence_type == "test_output" else diff_artifact
        if artifact is None:
            artifact = diff_artifact

        connection.execute(
            """
            INSERT INTO claims (
                id, case_id, run_id, claim_text, claim_type, status,
                metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim_id,
                case_id,
                run_id,
                claim.text,
                "agentguard_risk",
                "open",
                dumps_metadata({"severity": claim.severity}),
                now,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO evidence (
                id, case_id, artifact_id, claim_id, evidence_type, content,
                source_ref, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_uuid(),
                case_id,
                artifact.id,
                claim_id,
                claim.evidence_type,
                claim.evidence_content,
                claim.source_ref or artifact.id,
                dumps_metadata({"source": "agentguard_review"}),
                now,
                now,
            ),
        )
        claims_created += 1
        evidence_created += 1
    return claims_created, evidence_created


def _run_test_command(repo_root: Path, test_command: str | None) -> TestCommandResult | None:
    if test_command is None or not test_command.strip():
        return None

    args = _split_command(test_command)
    started_at = utc_now_iso()
    try:
        result = subprocess.run(
            args,
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
    except FileNotFoundError as error:
        raise ReviewServiceError(f"test command executable not found: {args[0]}") from error
    except subprocess.TimeoutExpired as error:
        return TestCommandResult(
            command=test_command,
            args=args,
            returncode=None,
            stdout=_timeout_output(error.stdout),
            stderr=_timeout_output(error.stderr),
            timed_out=True,
            started_at=started_at,
            finished_at=utc_now_iso(),
        )

    return TestCommandResult(
        command=test_command,
        args=args,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        timed_out=False,
        started_at=started_at,
        finished_at=utc_now_iso(),
    )


def _split_command(command: str) -> list[str]:
    try:
        args = shlex.split(command, posix=os.name != "nt")
    except ValueError as error:
        raise ReviewServiceError(f"could not parse test_command: {error}") from error
    if os.name == "nt":
        args = [_strip_outer_quotes(arg) for arg in args]
    if not args:
        raise ReviewServiceError("test_command is empty")
    return args


def _strip_outer_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _timeout_output(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _build_claim_specs(
    snapshot: GitSnapshot,
    test_result: TestCommandResult | None,
) -> list[ClaimSpec]:
    changed_files = snapshot.changed_files
    claims: list[ClaimSpec] = []

    deleted_files = [item.path for item in changed_files if item.status.startswith("D")]
    if deleted_files:
        claims.append(
            ClaimSpec(
                severity="high",
                text=f"Deleted files detected: {', '.join(deleted_files)}",
                evidence_type="git_diff",
                evidence_content=f"Deleted files: {', '.join(deleted_files)}",
                source_ref=deleted_files[0],
            )
        )

    sensitive_files = [item.path for item in changed_files if _is_sensitive_path(item.path)]
    if sensitive_files:
        claims.append(
            ClaimSpec(
                severity="medium",
                text=f"Sensitive backend/storage/action files changed: {', '.join(sensitive_files)}",
                evidence_type="git_diff",
                evidence_content=f"Sensitive path changes: {', '.join(sensitive_files)}",
                source_ref=sensitive_files[0],
            )
        )

    sensitive_untracked_notes = [
        note
        for note in snapshot.untracked_policy_notes
        if note.reason == "sensitive_untracked_file"
    ]
    if sensitive_untracked_notes:
        claims.append(
            ClaimSpec(
                severity="medium",
                text=(
                    "Sensitive untracked files were omitted from AgentGuard diff "
                    f"content: {_join_note_paths(sensitive_untracked_notes)}"
                ),
                evidence_type="git_diff",
                evidence_content=_format_untracked_policy_evidence(
                    sensitive_untracked_notes
                ),
                source_ref=sensitive_untracked_notes[0].path,
            )
        )

    oversized_untracked_notes = [
        note
        for note in snapshot.untracked_policy_notes
        if note.reason == "untracked_file_exceeds_diff_cap"
    ]
    if oversized_untracked_notes:
        claims.append(
            ClaimSpec(
                severity="info",
                text=(
                    "Oversized untracked files were omitted from AgentGuard diff "
                    f"content: {_join_note_paths(oversized_untracked_notes)}"
                ),
                evidence_type="git_diff",
                evidence_content=_format_untracked_policy_evidence(
                    oversized_untracked_notes
                ),
                source_ref=oversized_untracked_notes[0].path,
            )
        )

    if changed_files and _docs_only_change(changed_files):
        paths = _changed_paths(changed_files)
        claims.append(
            ClaimSpec(
                severity="info",
                text="Documentation or media-only change detected.",
                evidence_type="git_diff",
                evidence_content=_format_paths_evidence(
                    "All changed paths are documentation or media assets.",
                    paths,
                    "docs_only_change",
                ),
                source_ref=paths[0],
            )
        )

    workflow_paths = _paths_matching(changed_files, _is_workflow_path)
    if workflow_paths:
        claims.append(
            ClaimSpec(
                severity="medium",
                text="GitHub Actions workflow files changed.",
                evidence_type="git_diff",
                evidence_content=_format_paths_evidence(
                    "Workflow files changed.",
                    workflow_paths,
                    "workflow_changed",
                ),
                source_ref=workflow_paths[0],
            )
        )

    if workflow_paths and _workflow_permissions_changed(snapshot.diff_text):
        claims.append(
            ClaimSpec(
                severity="medium",
                text="GitHub Actions workflow permissions changed.",
                evidence_type="git_diff",
                evidence_content=_format_paths_evidence(
                    "Workflow permission surface changed.",
                    workflow_paths,
                    "ci_permissions_changed",
                ),
                source_ref=workflow_paths[0],
            )
        )

    script_paths = _paths_matching(changed_files, _is_script_path)
    command_surface_paths = _diff_command_surface_paths(snapshot.diff_text)
    if script_paths or command_surface_paths:
        affected_paths = _unique_paths([*script_paths, *command_surface_paths])
        claims.append(
            ClaimSpec(
                severity="medium",
                text="Script or command execution surface changed.",
                evidence_type="git_diff",
                evidence_content=_format_paths_evidence(
                    "Script paths or command-like diff content changed.",
                    affected_paths,
                    "script_or_command_surface_changed",
                ),
                source_ref=affected_paths[0] if affected_paths else None,
            )
        )

    backend_service_paths = _paths_matching(changed_files, _is_backend_service_path)
    if backend_service_paths and not _backend_tests_changed(changed_files):
        claims.append(
            ClaimSpec(
                severity="medium",
                text="Backend service code changed without backend test changes.",
                evidence_type="git_diff",
                evidence_content=_format_paths_evidence(
                    "Backend implementation paths changed but backend tests did not.",
                    backend_service_paths,
                    "backend_service_changed_without_tests",
                ),
                source_ref=backend_service_paths[0],
            )
        )

    frontend_source_paths = _paths_matching(changed_files, _is_frontend_source_path)
    if frontend_source_paths and not _frontend_tests_changed(changed_files):
        claims.append(
            ClaimSpec(
                severity="medium",
                text="Frontend source code changed without frontend test changes.",
                evidence_type="git_diff",
                evidence_content=_format_paths_evidence(
                    "Frontend source paths changed but frontend tests did not.",
                    frontend_source_paths,
                    "frontend_changed_without_tests",
                ),
                source_ref=frontend_source_paths[0],
            )
        )

    if _file_operation_code_changed(changed_files, snapshot.diff_text) and not _tests_changed(changed_files):
        file_paths = [item.path for item in changed_files]
        claims.append(
            ClaimSpec(
                severity="medium",
                text="File operation code changed without test changes.",
                evidence_type="git_diff",
                evidence_content=f"Changed files: {', '.join(file_paths)}",
                source_ref=file_paths[0] if file_paths else None,
            )
        )

    claims.extend(_semantic_claim_specs(snapshot))

    if test_result is not None and (test_result.timed_out or test_result.returncode != 0):
        detail = "timed out" if test_result.timed_out else f"exited with {test_result.returncode}"
        claims.append(
            ClaimSpec(
                severity="high",
                text=f"Test command failed: {detail}.",
                evidence_type="test_output",
                evidence_content=f"Command {test_result.command!r} {detail}.",
                source_ref=None,
            )
        )

    claims.append(
        ClaimSpec(
            severity="info",
            text=f"Changed file count: {len(changed_files)}.",
            evidence_type="git_diff",
            evidence_content=_changed_files_summary(changed_files),
            source_ref=None,
        )
    )
    return claims


def _semantic_claim_specs(snapshot: GitSnapshot) -> list[ClaimSpec]:
    claims: list[ClaimSpec] = []
    claims.extend(_codex_plugin_manifest_claims(snapshot))
    claims.extend(_codex_plugin_mcp_claims(snapshot))
    claims.extend(_codex_plugin_marketplace_claims(snapshot))
    claims.extend(_codex_skill_claims(snapshot))
    claims.extend(_changed_file_count_text_claims(snapshot))
    return claims


def _codex_plugin_manifest_claims(snapshot: GitSnapshot) -> list[ClaimSpec]:
    claims: list[ClaimSpec] = []
    for path in _changed_paths_matching(snapshot.changed_files, _is_codex_plugin_manifest_path):
        result = _read_json_file(snapshot.repo_root, path)
        if result.error:
            claims.append(
                ClaimSpec(
                    severity="medium",
                    text=f"Codex plugin manifest is not valid JSON: {path}",
                    evidence_type="git_diff",
                    evidence_content=f"{path}: {result.error}",
                    source_ref=path,
                )
            )
            continue

        data = result.data if isinstance(result.data, dict) else {}
        required = ("name", "version", "description", "skills", "mcpServers", "interface")
        missing = [field for field in required if not data.get(field)]
        interface = data.get("interface") if isinstance(data.get("interface"), dict) else {}
        interface_required = ("displayName", "shortDescription", "defaultPrompt")
        missing.extend(
            f"interface.{field}" for field in interface_required if not interface.get(field)
        )
        default_prompts = interface.get("defaultPrompt")
        if not isinstance(default_prompts, list) or len(default_prompts) == 0:
            missing.append("interface.defaultPrompt[]")
        if missing:
            claims.append(
                ClaimSpec(
                    severity="medium",
                    text=f"Codex plugin manifest is missing required fields: {path}",
                    evidence_type="git_diff",
                    evidence_content=f"Missing fields: {', '.join(missing)}",
                    source_ref=path,
                )
            )
            continue

        claims.append(
            ClaimSpec(
                severity="info",
                text=f"Codex plugin manifest declares required metadata and prompts: {path}",
                evidence_type="git_diff",
                evidence_content="\n".join(
                    [
                        f"Manifest: {path}",
                        f"name={data.get('name')}",
                        f"version={data.get('version')}",
                        f"skills={data.get('skills')}",
                        f"mcpServers={data.get('mcpServers')}",
                        "defaultPrompt:",
                        *[f"- {prompt}" for prompt in default_prompts],
                    ]
                ),
                source_ref=path,
            )
        )
    return claims


def _codex_plugin_mcp_claims(snapshot: GitSnapshot) -> list[ClaimSpec]:
    claims: list[ClaimSpec] = []
    for path in _changed_paths_matching(snapshot.changed_files, _is_plugin_mcp_config_path):
        result = _read_json_file(snapshot.repo_root, path)
        if result.error:
            claims.append(
                ClaimSpec(
                    severity="medium",
                    text=f"Codex plugin MCP config is not valid JSON: {path}",
                    evidence_type="git_diff",
                    evidence_content=f"{path}: {result.error}",
                    source_ref=path,
                )
            )
            continue

        data = result.data if isinstance(result.data, dict) else {}
        servers = data.get("mcpServers") if isinstance(data.get("mcpServers"), dict) else {}
        proofflow = servers.get("proofflow") if isinstance(servers.get("proofflow"), dict) else {}
        command = proofflow.get("command")
        env = proofflow.get("env") if isinstance(proofflow.get("env"), dict) else {}
        base_url = env.get("PROOFFLOW_BASE_URL")
        if command != "proofflow-mcp" or base_url != "http://127.0.0.1:8787":
            claims.append(
                ClaimSpec(
                    severity="medium",
                    text=f"ProofFlow MCP config does not point to the expected local server: {path}",
                    evidence_type="git_diff",
                    evidence_content=(
                        f"command={command!r}\n"
                        f"PROOFFLOW_BASE_URL={base_url!r}\n"
                        "Expected command='proofflow-mcp' and "
                        "PROOFFLOW_BASE_URL='http://127.0.0.1:8787'."
                    ),
                    source_ref=path,
                )
            )
            continue

        claims.append(
            ClaimSpec(
                severity="info",
                text=f"ProofFlow MCP config keeps the localhost trust boundary: {path}",
                evidence_type="git_diff",
                evidence_content=(
                    f"command={command}\n"
                    f"PROOFFLOW_BASE_URL={base_url}\n"
                    "The plugin points Codex at the local ProofFlow MCP server."
                ),
                source_ref=path,
            )
        )
    return claims


def _codex_plugin_marketplace_claims(snapshot: GitSnapshot) -> list[ClaimSpec]:
    claims: list[ClaimSpec] = []
    for path in _changed_paths_matching(snapshot.changed_files, _is_marketplace_config_path):
        result = _read_json_file(snapshot.repo_root, path)
        if result.error:
            claims.append(
                ClaimSpec(
                    severity="medium",
                    text=f"Codex marketplace config is not valid JSON: {path}",
                    evidence_type="git_diff",
                    evidence_content=f"{path}: {result.error}",
                    source_ref=path,
                )
            )
            continue

        data = result.data if isinstance(result.data, dict) else {}
        plugins = data.get("plugins") if isinstance(data.get("plugins"), list) else []
        entry = next(
            (
                item
                for item in plugins
                if isinstance(item, dict) and item.get("name") == "proofflow-maintainer"
            ),
            None,
        )
        source = entry.get("source") if isinstance(entry, dict) and isinstance(entry.get("source"), dict) else {}
        policy = entry.get("policy") if isinstance(entry, dict) and isinstance(entry.get("policy"), dict) else {}
        if (
            entry is None
            or source.get("path") != "./plugins/proofflow-maintainer"
            or policy.get("installation") != "AVAILABLE"
            or policy.get("authentication") != "ON_INSTALL"
        ):
            claims.append(
                ClaimSpec(
                    severity="medium",
                    text=f"Codex marketplace entry for ProofFlow Maintainer is incomplete: {path}",
                    evidence_type="git_diff",
                    evidence_content=(
                        "Expected plugin entry name='proofflow-maintainer', "
                        "source.path='./plugins/proofflow-maintainer', "
                        "installation='AVAILABLE', authentication='ON_INSTALL'."
                    ),
                    source_ref=path,
                )
            )
            continue

        claims.append(
            ClaimSpec(
                severity="info",
                text=f"Codex marketplace exposes the repo-local ProofFlow plugin: {path}",
                evidence_type="git_diff",
                evidence_content=(
                    "Marketplace entry:\n"
                    "name=proofflow-maintainer\n"
                    f"source.path={source.get('path')}\n"
                    f"installation={policy.get('installation')}\n"
                    f"authentication={policy.get('authentication')}"
                ),
                source_ref=path,
            )
        )
    return claims


def _codex_skill_claims(snapshot: GitSnapshot) -> list[ClaimSpec]:
    claims: list[ClaimSpec] = []
    for path in _changed_paths_matching(snapshot.changed_files, _is_codex_skill_path):
        text = _read_text_file(snapshot.repo_root, path)
        required_terms = (
            "proofflow_health",
            "proofflow_review",
            "proofflow_triage_issue",
            "proofflow_export_packet",
            "merge-base",
            "base_ref",
            "GITHUB_BASE_REF",
        )
        missing = [term for term in required_terms if term not in text]
        if missing:
            claims.append(
                ClaimSpec(
                    severity="medium",
                    text=f"Codex skill is missing ProofFlow review guardrails: {path}",
                    evidence_type="git_diff",
                    evidence_content=f"Missing required terms: {', '.join(missing)}",
                    source_ref=path,
                )
            )
            continue

        claims.append(
            ClaimSpec(
                severity="info",
                text=f"Codex skill documents PR-base review and Proof Packet export guardrails: {path}",
                evidence_type="git_diff",
                evidence_content=(
                    "Skill includes ProofFlow health, review, issue triage, export, "
                    "PR base, GITHUB_BASE_REF, and merge-base guidance."
                ),
                source_ref=path,
            )
        )
    return claims


def _changed_file_count_text_claims(snapshot: GitSnapshot) -> list[ClaimSpec]:
    claims: list[ClaimSpec] = []
    changed_paths = _changed_paths(snapshot.changed_files)
    total_count = len(changed_paths)
    for path in _changed_paths_matching(snapshot.changed_files, _is_markdown_path):
        text = _read_text_file(snapshot.repo_root, path)
        for match in _count_claim_pattern().finditer(text):
            expected = _count_word_value(match.group("count"))
            if expected is None:
                continue
            scope = match.group("scope") or ""
            actual = (
                _changed_files_under_prefix(changed_paths, "plugins/proofflow-maintainer/")
                if "plugin" in scope.lower()
                else total_count
            )
            if expected == actual:
                continue
            claims.append(
                ClaimSpec(
                    severity="medium",
                    text=f"Markdown changed-file count statement appears inconsistent: {path}",
                    evidence_type="git_diff",
                    evidence_content="\n".join(
                        [
                            f"Statement: {match.group(0).strip()}",
                            f"Stated count: {expected}",
                            f"Actual {'plugin ' if 'plugin' in scope.lower() else ''}changed file count: {actual}",
                            "Changed files:",
                            *[f"- {changed_path}" for changed_path in changed_paths],
                        ]
                    ),
                    source_ref=path,
                )
            )
    return claims


def _risk_level(
    changed_files: list[ChangedFile],
    claims: list[ClaimSpec],
    test_result: TestCommandResult | None,
) -> str:
    if not changed_files and not _test_failed(test_result):
        return "low"
    highest = "info"
    for claim in claims:
        if SEVERITY_ORDER[claim.severity] > SEVERITY_ORDER[highest]:
            highest = claim.severity
    return highest


def _test_failed(test_result: TestCommandResult | None) -> bool:
    return test_result is not None and (test_result.timed_out or test_result.returncode != 0)


def _test_status(test_result: TestCommandResult | None) -> str:
    if test_result is None:
        return "not_run"
    if test_result.timed_out:
        return "timeout"
    if test_result.returncode == 0:
        return "passed"
    return "failed"


def _changed_paths(changed_files: list[ChangedFile]) -> list[str]:
    return [item.path for item in changed_files]


def _unique_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for path in paths:
        if path not in seen:
            unique.append(path)
            seen.add(path)
    return unique


def _paths_matching(
    changed_files: list[ChangedFile],
    predicate: Any,
) -> list[str]:
    return [item.path for item in changed_files if predicate(item.path)]


def _changed_paths_matching(
    changed_files: list[ChangedFile],
    predicate: Any,
) -> list[str]:
    return _paths_matching(changed_files, predicate)


def _format_paths_evidence(summary: str, paths: list[str], trigger: str) -> str:
    lines = [summary, f"Trigger: {trigger}", "Affected paths:"]
    lines.extend(f"- {path}" for path in paths)
    return "\n".join(lines)


def _docs_only_change(changed_files: list[ChangedFile]) -> bool:
    return all(_is_documentation_or_media_path(item.path) for item in changed_files)


def _is_documentation_or_media_path(path: str) -> bool:
    normalized = path.lower().replace("\\", "/")
    name = Path(normalized).name
    suffix = Path(normalized).suffix
    if name in {"readme.md", "readme.zh-cn.md", "changelog.md"}:
        return True
    if normalized.startswith("docs/"):
        return True
    if name.startswith("release_notes") and suffix == ".md":
        return True
    return suffix in {
        ".md",
        ".markdown",
        ".txt",
        ".rst",
        ".svg",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
    }


def _is_workflow_path(path: str) -> bool:
    return path.lower().replace("\\", "/").startswith(".github/workflows/")


def _is_script_path(path: str) -> bool:
    return path.lower().replace("\\", "/").startswith("scripts/")


def _is_backend_service_path(path: str) -> bool:
    normalized = path.lower().replace("\\", "/")
    return normalized.startswith("backend/proofflow/")


def _is_frontend_source_path(path: str) -> bool:
    normalized = path.lower().replace("\\", "/")
    return normalized.startswith("frontend/src/") and not _is_frontend_test_path(path)


def _backend_tests_changed(changed_files: list[ChangedFile]) -> bool:
    return any(_is_backend_test_path(item.path) for item in changed_files)


def _frontend_tests_changed(changed_files: list[ChangedFile]) -> bool:
    return any(_is_frontend_test_path(item.path) for item in changed_files)


def _is_backend_test_path(path: str) -> bool:
    normalized = path.lower().replace("\\", "/")
    return normalized.startswith("backend/tests/") or normalized.startswith("tests/")


def _is_frontend_test_path(path: str) -> bool:
    normalized = path.lower().replace("\\", "/")
    return (
        normalized.startswith("frontend/src/")
        and (
            ".test." in Path(normalized).name
            or ".spec." in Path(normalized).name
            or "/__tests__/" in normalized
        )
    ) or normalized.startswith("frontend/tests/")


def _is_codex_plugin_manifest_path(path: str) -> bool:
    return _normalize_path(path).endswith("/.codex-plugin/plugin.json")


def _is_plugin_mcp_config_path(path: str) -> bool:
    normalized = _normalize_path(path)
    return normalized.startswith("plugins/") and normalized.endswith("/.mcp.json")


def _is_marketplace_config_path(path: str) -> bool:
    return _normalize_path(path) == ".agents/plugins/marketplace.json"


def _is_codex_skill_path(path: str) -> bool:
    normalized = _normalize_path(path)
    return normalized.startswith("plugins/") and normalized.endswith("/skill.md")


def _is_markdown_path(path: str) -> bool:
    return Path(_normalize_path(path)).suffix.lower() in {".md", ".markdown"}


def _workflow_permissions_changed(diff_text: str) -> bool:
    permission_keys = (
        "permissions:",
        "contents:",
        "pull-requests:",
        "issues:",
        "actions:",
        "checks:",
        "id-token:",
        "security-events:",
    )
    in_workflow_file = False
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            in_workflow_file = _diff_header_is_workflow(line)
            continue
        if not in_workflow_file:
            continue
        stripped = line.strip().lower()
        if not stripped.startswith(("+", "-")):
            continue
        if stripped.startswith(("+++", "---")):
            continue
        if any(key in stripped for key in permission_keys):
            return True
    return False


def _diff_header_is_workflow(line: str) -> bool:
    parts = line.split()
    if len(parts) < 4:
        return False
    paths = [part[2:] if part.startswith(("a/", "b/")) else part for part in parts[2:4]]
    return any(_is_workflow_path(path) for path in paths)


def _diff_command_surface_paths(diff_text: str) -> list[str]:
    command_keywords = (
        "run:",
        "subprocess",
        "invoke-restmethod",
        "curl ",
        "wget ",
        "bash ",
        "powershell",
        "cmd /c",
        "python -m",
        "npm ",
        "pip ",
    )
    paths: list[str] = []
    current_path: str | None = None
    inspect_current_path = False
    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            current_path = _diff_header_path(line)
            inspect_current_path = current_path is not None and not _is_documentation_or_media_path(
                current_path
            )
            continue
        if current_path is None or not inspect_current_path:
            continue
        stripped = line.strip().lower()
        if not stripped.startswith(("+", "-")):
            continue
        if stripped.startswith(("+++", "---")):
            continue
        if any(keyword in stripped for keyword in command_keywords):
            paths.append(current_path)
    return _unique_paths(paths)


def _diff_header_path(line: str) -> str | None:
    parts = line.split()
    if len(parts) < 4:
        return None
    path = parts[3]
    if path.startswith("b/"):
        return path[2:]
    if path.startswith("a/"):
        return path[2:]
    return path


def _is_sensitive_path(path: str) -> bool:
    normalized = path.lower().replace("\\", "/")
    parts = normalized.split("/")
    return (
        "migrations/" in normalized
        or "storage/" in normalized
        or any(part == "db" or part.startswith("db.") for part in parts)
        or any(part == "actions" or part.startswith("actions.") for part in parts)
    )


def _file_operation_code_changed(changed_files: list[ChangedFile], diff_text: str) -> bool:
    path_keywords = ("file_scanner", "action_service", "action_suggestion", "localproof")
    diff_keywords = (
        "shutil.move",
        ".unlink(",
        ".rename(",
        ".replace(",
        "os.remove",
        "remove-item",
        "move_file",
        "rename_file",
    )
    normalized_diff = diff_text.lower()
    return any(
        any(keyword in item.path.lower() for keyword in path_keywords)
        for item in changed_files
    ) or any(keyword in normalized_diff for keyword in diff_keywords)


def _tests_changed(changed_files: list[ChangedFile]) -> bool:
    for item in changed_files:
        normalized = item.path.lower().replace("\\", "/")
        if normalized.startswith("tests/") or "/tests/" in f"/{normalized}":
            return True
        if Path(normalized).name.startswith("test_"):
            return True
    return False


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").lower()


def _repo_file_path(repo_root: Path, relative_path: str) -> Path:
    return repo_root / relative_path.replace("/", os.sep)


def _read_text_file(repo_root: Path, relative_path: str) -> str:
    path = _repo_file_path(repo_root, relative_path)
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _read_json_file(repo_root: Path, relative_path: str) -> JsonReadResult:
    text = _read_text_file(repo_root, relative_path)
    if not text:
        return JsonReadResult(data=None, error="file is missing or empty")
    try:
        return JsonReadResult(data=json.loads(text))
    except json.JSONDecodeError as error:
        return JsonReadResult(data=None, error=str(error))


def _changed_files_under_prefix(paths: list[str], prefix: str) -> int:
    normalized_prefix = _normalize_path(prefix)
    return sum(1 for path in paths if _normalize_path(path).startswith(normalized_prefix))


def _count_claim_pattern() -> re.Pattern[str]:
    count_words = "one|two|three|four|five|six|seven|eight|nine|ten"
    return re.compile(
        rf"\b(?P<count>{count_words}|\d+)\s+"
        r"(?P<scope>plugin\s+)?"
        r"files?\s+(?:changed|in\s+the\s+PR)",
        re.IGNORECASE,
    )


def _count_word_value(value: str) -> int | None:
    words = {
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
    }
    lowered = value.lower()
    if lowered in words:
        return words[lowered]
    try:
        return int(value)
    except ValueError:
        return None


def _changed_file_metadata(changed_files: list[ChangedFile]) -> list[dict[str, str]]:
    return [
        {"path": item.path, "status": item.status, "source": item.source}
        for item in changed_files
    ]


def _untracked_policy_note_metadata(
    notes: list[UntrackedFilePolicyNote],
) -> list[dict[str, Any]]:
    metadata: list[dict[str, Any]] = []
    for note in notes:
        item: dict[str, Any] = {
            "path": note.path,
            "reason": note.reason,
            "truncated": note.truncated,
        }
        if note.size_bytes is not None:
            item["size_bytes"] = note.size_bytes
        if note.cap_bytes is not None:
            item["cap_bytes"] = note.cap_bytes
        metadata.append(item)
    return metadata


def _join_note_paths(notes: list[UntrackedFilePolicyNote]) -> str:
    return ", ".join(note.path for note in notes)


def _format_untracked_policy_evidence(notes: list[UntrackedFilePolicyNote]) -> str:
    lines: list[str] = []
    for note in notes:
        parts = [f"{note.path}: {note.reason}"]
        if note.size_bytes is not None:
            parts.append(f"size_bytes={note.size_bytes}")
        if note.cap_bytes is not None:
            parts.append(f"cap_bytes={note.cap_bytes}")
        if note.truncated:
            parts.append("truncated=true")
        lines.append("; ".join(parts))
    return "\n".join(lines)


def _changed_files_summary(changed_files: list[ChangedFile]) -> str:
    if not changed_files:
        return "No changed files detected."
    return "\n".join(
        f"{item.status}\t{item.path}\t{item.source}" for item in changed_files
    )


def _format_test_output(result: TestCommandResult) -> str:
    return "\n".join(
        [
            f"$ {result.command}",
            f"timed_out: {result.timed_out}",
            f"returncode: {result.returncode}",
            "",
            "stdout:",
            result.stdout or "",
            "",
            "stderr:",
            result.stderr or "",
        ]
    )
