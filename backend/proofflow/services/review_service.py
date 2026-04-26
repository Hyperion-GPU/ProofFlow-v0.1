from dataclasses import dataclass
from pathlib import Path
from typing import Any

import hashlib
import os
import shlex
import subprocess

from proofflow.db import connect, new_uuid, utc_now_iso
from proofflow.models.schemas import (
    AgentGuardArtifactRef,
    AgentGuardReviewRequest,
    AgentGuardReviewResponse,
)
from proofflow.services.git_service import ChangedFile, GitSnapshot, inspect_working_tree
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
