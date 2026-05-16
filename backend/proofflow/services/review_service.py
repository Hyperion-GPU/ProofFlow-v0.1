from dataclasses import dataclass
from pathlib import Path
from typing import Any

import hashlib
import os
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
