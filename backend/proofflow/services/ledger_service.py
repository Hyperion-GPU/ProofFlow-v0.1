from __future__ import annotations

from typing import Any

import hashlib
import json
import re

from proofflow.db import connect, new_uuid, utc_now_iso
from proofflow.models.schemas import (
    CaseCreate,
    LedgerAlgorithmDecisionCreateRequest,
    LedgerAlgorithmDecisionResponse,
    LedgerClaimCreateRequest,
    LedgerClaimCreateResponse,
    LedgerCostBudgetCreateRequest,
    LedgerCostBudgetResponse,
    LedgerEvaluationResponse,
    LedgerEventCreateRequest,
    LedgerEventResponse,
    LedgerEvidenceCreateRequest,
    LedgerEvidenceCreateResponse,
    LedgerFinishRequest,
    LedgerFinishResponse,
    WorkContractStartRequest,
    WorkContractStartResponse,
    WorkSnapshotRequest,
    WorkSnapshotResponse,
)
from proofflow.services import case_service
from proofflow.services.errors import NotFoundError
from proofflow.services.git_service import (
    current_head_sha,
    inspect_working_tree,
    status_short,
)
from proofflow.services.json_utils import dumps_metadata, loads_metadata

TEXT_CHUNK_LINES = 200
LEDGER_KIND = "agent_work_ledger"
LEDGER_SOURCE = "agent_work_ledger"
KNOWN_ARTIFACT_TYPES = {
    "file",
    "text",
    "code",
    "image",
    "log",
    "pdf",
    "diff",
    "git_diff",
    "note",
    "command_output",
    "test_result",
    "test_output",
    "proof_packet",
    "screenshot",
    "issue",
    "algorithm_decision",
    "cost_budget",
}
CLOSED_CLAIM_STATUSES = {"closed", "resolved", "accepted", "rejected"}


class LedgerServiceError(ValueError):
    """Raised when a Ledger workflow request is invalid."""


def start_work_contract(payload: WorkContractStartRequest) -> WorkContractStartResponse:
    contract = payload.model_dump()
    case = case_service.create_case(
        CaseCreate(
            title=f"Agent work ledger: {payload.objective}",
            kind=LEDGER_KIND,
            status="active",
            summary=payload.objective,
            metadata={
                "source": LEDGER_SOURCE,
                "status": "active",
                "contract": contract,
                **contract,
            },
        )
    )
    return WorkContractStartResponse(case_id=case.id, status="active", case=case)


def record_event(case_id: str, payload: LedgerEventCreateRequest) -> LedgerEventResponse:
    _require_ledger_case(case_id)
    sequence = _next_event_sequence(case_id)
    event_type = _slug(payload.event_type)
    name = f"ledger-event-{event_type}-{sequence:03d}.md"
    content = _format_event_content(sequence, payload)
    metadata = {
        "source": LEDGER_SOURCE,
        "ledger_item_type": "event",
        "event_type": payload.event_type,
        "summary": payload.summary,
        "sequence": sequence,
        **payload.metadata,
    }
    artifact = _insert_text_artifact(
        case_id=case_id,
        kind="log",
        name=name,
        content=content,
        role="supporting",
        uri=f"ledger://{case_id}/events/{sequence:03d}",
        metadata=metadata,
        mime_type="text/markdown",
    )
    return LedgerEventResponse(
        case_id=case_id,
        artifact_id=artifact["id"],
        sequence=sequence,
        event_type=payload.event_type,
        name=name,
        created_at=artifact["created_at"],
    )


def record_algorithm_decision(
    case_id: str,
    payload: LedgerAlgorithmDecisionCreateRequest,
) -> LedgerAlgorithmDecisionResponse:
    _require_ledger_case(case_id)
    sequence = _next_ledger_item_sequence(case_id, "algorithm-decision")
    name = f"ledger-algorithm-decision-{sequence:03d}.md"
    content = _format_algorithm_decision_content(sequence, payload)
    metadata = {
        "source": LEDGER_SOURCE,
        "ledger_item_type": "algorithm_decision",
        "summary": payload.summary,
        "chosen_approach": payload.chosen_approach,
        "rationale": payload.rationale,
        "alternatives_considered": payload.alternatives_considered,
        "invariants": payload.invariants,
        "forbidden_approaches": payload.forbidden_approaches,
        "sequence": sequence,
        **payload.metadata,
    }
    artifact = _insert_text_artifact(
        case_id=case_id,
        kind="algorithm_decision",
        name=name,
        content=content,
        role="supporting",
        uri=f"ledger://{case_id}/algorithm-decisions/{sequence:03d}",
        metadata=metadata,
        mime_type="text/markdown",
    )
    return LedgerAlgorithmDecisionResponse(
        case_id=case_id,
        artifact_id=artifact["id"],
        sequence=sequence,
        summary=payload.summary,
        name=name,
        created_at=artifact["created_at"],
    )


def record_cost_budget(
    case_id: str,
    payload: LedgerCostBudgetCreateRequest,
) -> LedgerCostBudgetResponse:
    _require_ledger_case(case_id)
    sequence = _next_ledger_item_sequence(case_id, "cost-budget")
    name = f"ledger-cost-budget-{sequence:03d}.md"
    content = _format_cost_budget_content(sequence, payload)
    metadata = {
        "source": LEDGER_SOURCE,
        "ledger_item_type": "cost_budget",
        "summary": payload.summary,
        "budget": payload.budget,
        "expected_operations": payload.expected_operations,
        "limits": payload.limits,
        "sequence": sequence,
        **payload.metadata,
    }
    artifact = _insert_text_artifact(
        case_id=case_id,
        kind="cost_budget",
        name=name,
        content=content,
        role="supporting",
        uri=f"ledger://{case_id}/cost-budgets/{sequence:03d}",
        metadata=metadata,
        mime_type="text/markdown",
    )
    return LedgerCostBudgetResponse(
        case_id=case_id,
        artifact_id=artifact["id"],
        sequence=sequence,
        summary=payload.summary,
        name=name,
        created_at=artifact["created_at"],
    )


def finish_work_ledger(case_id: str, payload: LedgerFinishRequest) -> LedgerFinishResponse:
    case = _require_ledger_case(case_id)
    artifacts = _load_case_artifacts(case_id)
    if _latest_snapshot(artifacts, "final") is None:
        raise LedgerServiceError("final snapshot is required before finishing a ledger")

    latest_evaluation = _latest_evaluation(case_id)
    status_value = "finished"
    if latest_evaluation is not None and latest_evaluation != "ready_for_review":
        status_value = "finished_with_risks"

    metadata = dict(case["metadata"])
    finished_at = utc_now_iso()
    metadata["status"] = status_value
    metadata["finished_at"] = finished_at
    if latest_evaluation is not None:
        metadata["latest_evaluation_status"] = latest_evaluation
    if payload.summary is not None:
        metadata["finish_summary"] = payload.summary

    with connect() as connection:
        result = connection.execute(
            """
            UPDATE cases
            SET metadata_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (dumps_metadata(metadata), finished_at, case_id),
        )
        connection.commit()
    if result.rowcount == 0:
        raise NotFoundError(f"case not found: {case_id}")

    return LedgerFinishResponse(
        case_id=case_id,
        status=status_value,
        finished_at=finished_at,
        metadata=metadata,
    )


def capture_snapshot(case_id: str, payload: WorkSnapshotRequest) -> WorkSnapshotResponse:
    _require_ledger_case(case_id)
    snapshot = inspect_working_tree(
        payload.repo_path,
        payload.base_ref,
        payload.include_untracked,
    )
    head_sha = current_head_sha(str(snapshot.repo_root))
    git_status = status_short(str(snapshot.repo_root))
    diff_text = snapshot.diff_text or "No diff content captured."
    encoded = diff_text.encode("utf-8")
    diff_sha256 = hashlib.sha256(encoded).hexdigest()
    changed_files = [changed_file.path for changed_file in snapshot.changed_files]
    name = f"ledger-{payload.phase}-diff.patch"
    metadata = {
        "source": LEDGER_SOURCE,
        "ledger_item_type": "snapshot",
        "repo_path": str(snapshot.repo_root),
        "phase": payload.phase,
        "head_sha": head_sha,
        "base_ref": payload.base_ref,
        "include_untracked": payload.include_untracked,
        "changed_files": [
            {
                "path": changed_file.path,
                "status": changed_file.status,
                "source": changed_file.source,
            }
            for changed_file in snapshot.changed_files
        ],
        "changed_file_count": len(changed_files),
        "git_status": git_status,
        "diff_sha256": diff_sha256,
        "diff_line_count": len(diff_text.splitlines()),
        "untracked_policy_notes": [
            {
                "path": note.path,
                "reason": note.reason,
                "size_bytes": note.size_bytes,
                "cap_bytes": note.cap_bytes,
                "truncated": note.truncated,
            }
            for note in snapshot.untracked_policy_notes
        ],
    }
    artifact = _insert_text_artifact(
        case_id=case_id,
        kind="git_diff",
        name=name,
        content=diff_text,
        role="primary" if payload.phase in {"start", "final"} else "supporting",
        uri=f"ledger://{case_id}/snapshots/{payload.phase}",
        metadata=metadata,
        mime_type="text/x-diff",
    )
    return WorkSnapshotResponse(
        case_id=case_id,
        artifact_id=artifact["id"],
        phase=payload.phase,
        head_sha=head_sha,
        base_ref=payload.base_ref,
        changed_files=changed_files,
        diff_sha256=diff_sha256,
    )


def record_evidence(
    case_id: str,
    payload: LedgerEvidenceCreateRequest,
) -> LedgerEvidenceCreateResponse:
    _require_ledger_case(case_id)
    artifact_kind = (
        payload.evidence_type
        if payload.evidence_type in KNOWN_ARTIFACT_TYPES
        else "text"
    )
    name = f"ledger-evidence-{_slug(payload.evidence_type)}-{_next_evidence_sequence(case_id):03d}.txt"
    artifact = _insert_text_artifact(
        case_id=case_id,
        kind=artifact_kind,
        name=name,
        content=payload.content,
        role="supporting",
        uri=f"ledger://{case_id}/evidence/{name}",
        metadata={
            "source": LEDGER_SOURCE,
            "ledger_item_type": "evidence",
            "evidence_type": payload.evidence_type,
            **payload.metadata,
        },
        mime_type="text/plain",
    )
    now = utc_now_iso()
    evidence_id = new_uuid()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO evidence (
                id, case_id, artifact_id, claim_id, evidence_type, content,
                source_ref, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_id,
                case_id,
                artifact["id"],
                None,
                payload.evidence_type,
                payload.content,
                payload.source_ref or artifact["id"],
                dumps_metadata({"source": LEDGER_SOURCE, **payload.metadata}),
                now,
                now,
            ),
        )
        connection.commit()
    return LedgerEvidenceCreateResponse(
        case_id=case_id,
        artifact_id=artifact["id"],
        evidence_id=evidence_id,
        evidence_type=payload.evidence_type,
        created_at=now,
    )


def record_claim(case_id: str, payload: LedgerClaimCreateRequest) -> LedgerClaimCreateResponse:
    _require_ledger_case(case_id)
    rows = _load_evidence_rows(case_id, payload.evidence_ids)
    found_ids = {row["id"] for row in rows}
    missing_ids = [evidence_id for evidence_id in payload.evidence_ids if evidence_id not in found_ids]
    if missing_ids:
        raise LedgerServiceError(f"evidence not found for case: {', '.join(missing_ids)}")

    now = utc_now_iso()
    claim_id = new_uuid()
    with connect() as connection:
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
                None,
                payload.claim_text,
                "ledger_claim",
                "open",
                dumps_metadata({"source": LEDGER_SOURCE, "severity": payload.severity}),
                now,
                now,
            ),
        )
        connection.executemany(
            """
            UPDATE evidence
            SET claim_id = ?, updated_at = ?
            WHERE case_id = ? AND id = ?
            """,
            [(claim_id, now, case_id, evidence_id) for evidence_id in payload.evidence_ids],
        )
        connection.commit()
    return LedgerClaimCreateResponse(
        case_id=case_id,
        claim_id=claim_id,
        evidence_ids=payload.evidence_ids,
        created_at=now,
    )


def evaluate_contract(case_id: str) -> LedgerEvaluationResponse:
    case = _require_ledger_case(case_id)
    contract = _contract_from_metadata(case["metadata"])
    artifacts = _load_case_artifacts(case_id)
    evidence_rows = _load_case_evidence(case_id)
    claims = _load_case_claims(case_id)
    decisions = _load_case_decisions(case_id)

    passed: list[str] = []
    failed: list[str] = []
    warnings: list[str] = []
    missing_evidence: list[str] = []
    scope_violations: list[str] = []

    _evaluate_required_tests(contract, artifacts, evidence_rows, passed, failed)
    _evaluate_evidence_requirements(
        contract,
        artifacts,
        evidence_rows,
        passed,
        failed,
        missing_evidence,
    )
    _evaluate_algorithm_decision(contract, artifacts, passed, failed, missing_evidence)
    _evaluate_cost_budget(contract, artifacts, passed, failed, missing_evidence)
    _evaluate_scope(contract, artifacts, passed, failed, warnings, scope_violations)
    _evaluate_open_risks(claims, decisions, passed, failed)

    status_value = _evaluation_status(failed)
    run_id = _insert_evaluation_run(
        case_id,
        status_value,
        passed,
        failed,
        warnings,
        missing_evidence,
        scope_violations,
    )
    return LedgerEvaluationResponse(
        case_id=case_id,
        run_id=run_id,
        status=status_value,
        passed=passed,
        failed=failed,
        warnings=warnings,
        missing_evidence=missing_evidence,
        scope_violations=scope_violations,
    )


def _require_ledger_case(case_id: str) -> dict[str, Any]:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT id, title, case_type, status, summary, metadata_json, created_at, updated_at
            FROM cases
            WHERE id = ?
            """,
            (case_id,),
        ).fetchone()
    if row is None:
        raise NotFoundError(f"case not found: {case_id}")
    if row["case_type"] != LEDGER_KIND:
        raise LedgerServiceError(f"case is not an agent work ledger: {case_id}")
    return {
        "id": row["id"],
        "title": row["title"],
        "kind": row["case_type"],
        "status": row["status"],
        "summary": row["summary"],
        "metadata": loads_metadata(row["metadata_json"]),
    }


def _next_event_sequence(case_id: str) -> int:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM case_artifacts
            JOIN artifacts ON artifacts.id = case_artifacts.artifact_id
            WHERE case_artifacts.case_id = ?
              AND artifacts.name LIKE 'ledger-event-%'
            """,
            (case_id,),
        ).fetchone()
    return int(row[0]) + 1


def _next_evidence_sequence(case_id: str) -> int:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM case_artifacts
            JOIN artifacts ON artifacts.id = case_artifacts.artifact_id
            WHERE case_artifacts.case_id = ?
              AND artifacts.name LIKE 'ledger-evidence-%'
            """,
            (case_id,),
        ).fetchone()
    return int(row[0]) + 1


def _next_ledger_item_sequence(case_id: str, name_prefix: str) -> int:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*)
            FROM case_artifacts
            JOIN artifacts ON artifacts.id = case_artifacts.artifact_id
            WHERE case_artifacts.case_id = ?
              AND artifacts.name LIKE ?
            """,
            (case_id, f"ledger-{name_prefix}-%"),
        ).fetchone()
    return int(row[0]) + 1


def _insert_text_artifact(
    *,
    case_id: str,
    kind: str,
    name: str,
    content: str,
    role: str,
    uri: str,
    metadata: dict[str, Any],
    mime_type: str,
) -> dict[str, str]:
    now = utc_now_iso()
    artifact_id = new_uuid()
    encoded = content.encode("utf-8")
    with connect() as connection:
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
                uri,
                name,
                mime_type,
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
        connection.commit()
    return {"id": artifact_id, "created_at": now}


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
                        "source": LEDGER_SOURCE,
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


def _format_event_content(sequence: int, payload: LedgerEventCreateRequest) -> str:
    lines = [
        f"# Ledger Event {sequence:03d}: {payload.summary}",
        "",
        f"- Type: `{payload.event_type}`",
        "",
    ]
    if payload.content:
        lines.extend([payload.content, ""])
    if payload.metadata:
        lines.extend(["## Metadata", "", "```json"])
        lines.append(json.dumps(payload.metadata, indent=2, sort_keys=True))
        lines.extend(["```", ""])
    return "\n".join(lines).rstrip() + "\n"


def _format_algorithm_decision_content(
    sequence: int,
    payload: LedgerAlgorithmDecisionCreateRequest,
) -> str:
    lines = [
        f"# Algorithm Decision {sequence:03d}: {payload.summary}",
        "",
        "## Chosen Approach",
        "",
        payload.chosen_approach,
        "",
        "## Rationale",
        "",
        payload.rationale,
        "",
    ]
    _append_list_section(lines, "Alternatives Considered", payload.alternatives_considered)
    _append_list_section(lines, "Invariants", payload.invariants)
    _append_list_section(lines, "Forbidden Approaches", payload.forbidden_approaches)
    if payload.metadata:
        lines.extend(["## Metadata", "", "```json"])
        lines.append(json.dumps(payload.metadata, indent=2, sort_keys=True))
        lines.extend(["```", ""])
    return "\n".join(lines).rstrip() + "\n"


def _format_cost_budget_content(
    sequence: int,
    payload: LedgerCostBudgetCreateRequest,
) -> str:
    lines = [
        f"# Cost Budget {sequence:03d}: {payload.summary}",
        "",
    ]
    if payload.budget:
        lines.extend(["## Budget", "", "```json"])
        lines.append(json.dumps(payload.budget, indent=2, sort_keys=True))
        lines.extend(["```", ""])
    _append_list_section(lines, "Expected Operations", payload.expected_operations)
    _append_list_section(lines, "Limits", payload.limits)
    if payload.metadata:
        lines.extend(["## Metadata", "", "```json"])
        lines.append(json.dumps(payload.metadata, indent=2, sort_keys=True))
        lines.extend(["```", ""])
    return "\n".join(lines).rstrip() + "\n"


def _append_list_section(lines: list[str], title: str, values: list[str]) -> None:
    if not values:
        return
    lines.extend([f"## {title}", ""])
    for value in values:
        lines.append(f"- {value}")
    lines.append("")


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip().lower()).strip(".-")
    return slug or "item"


def _contract_from_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    contract = metadata.get("contract")
    if isinstance(contract, dict):
        return contract
    return {
        key: metadata.get(key)
        for key in (
            "objective",
            "repo_path",
            "allowed_scope",
            "forbidden_actions",
            "required_tests",
            "done_criteria",
            "evidence_requirements",
            "algorithm_requirements",
            "cost_budget",
        )
    }


def _load_case_artifacts(case_id: str) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT artifacts.id, artifacts.artifact_type, artifacts.name, artifacts.uri,
                   artifacts.metadata_json, artifacts.created_at
            FROM case_artifacts
            JOIN artifacts ON artifacts.id = case_artifacts.artifact_id
            WHERE case_artifacts.case_id = ?
            ORDER BY artifacts.created_at ASC, artifacts.id ASC
            """,
            (case_id,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "artifact_type": row["artifact_type"],
            "name": row["name"],
            "uri": row["uri"],
            "metadata": loads_metadata(row["metadata_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def _load_case_evidence(case_id: str) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, artifact_id, claim_id, evidence_type, content, source_ref,
                   metadata_json, created_at
            FROM evidence
            WHERE case_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (case_id,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "artifact_id": row["artifact_id"],
            "claim_id": row["claim_id"],
            "evidence_type": row["evidence_type"],
            "content": row["content"],
            "source_ref": row["source_ref"],
            "metadata": loads_metadata(row["metadata_json"]),
        }
        for row in rows
    ]


def _load_evidence_rows(case_id: str, evidence_ids: list[str]) -> list[Any]:
    placeholders = ",".join("?" for _ in evidence_ids)
    with connect() as connection:
        return connection.execute(
            f"""
            SELECT id, claim_id
            FROM evidence
            WHERE case_id = ? AND id IN ({placeholders})
            """,
            (case_id, *evidence_ids),
        ).fetchall()


def _load_case_claims(case_id: str) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, claim_text, claim_type, status, metadata_json
            FROM claims
            WHERE case_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (case_id,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "claim_text": row["claim_text"],
            "claim_type": row["claim_type"],
            "status": row["status"],
            "metadata": loads_metadata(row["metadata_json"]),
        }
        for row in rows
    ]


def _load_case_decisions(case_id: str) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, title, status, rationale, result, metadata_json
            FROM decisions
            WHERE case_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (case_id,),
        ).fetchall()
    return [
        {
            "id": row["id"],
            "title": row["title"],
            "status": row["status"],
            "rationale": row["rationale"],
            "result": row["result"],
            "metadata": loads_metadata(row["metadata_json"]),
        }
        for row in rows
    ]


def _evaluate_required_tests(
    contract: dict[str, Any],
    artifacts: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
    passed: list[str],
    failed: list[str],
) -> None:
    required_tests = _string_list(contract.get("required_tests"))
    if not required_tests:
        passed.append("required_tests_not_configured")
        return

    haystack = _ledger_haystack(artifacts, evidence_rows)
    missing = [command for command in required_tests if command.lower() not in haystack]
    if missing:
        failed.append("needs_tests")
    else:
        passed.append("required_tests")


def _evaluate_evidence_requirements(
    contract: dict[str, Any],
    artifacts: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
    passed: list[str],
    failed: list[str],
    missing_evidence: list[str],
) -> None:
    requirements = _string_list(contract.get("evidence_requirements"))
    if not requirements:
        passed.append("evidence_requirements_not_configured")
        return

    available = {
        artifact["artifact_type"]
        for artifact in artifacts
    } | {
        str(artifact["metadata"].get("ledger_item_type"))
        for artifact in artifacts
        if artifact["metadata"].get("ledger_item_type")
    } | {row["evidence_type"] for row in evidence_rows}
    for requirement in requirements:
        if requirement not in available:
            missing_evidence.append(requirement)
    if missing_evidence:
        failed.append("incomplete_evidence")
    else:
        passed.append("evidence_requirements")


def _evaluate_algorithm_decision(
    contract: dict[str, Any],
    artifacts: list[dict[str, Any]],
    passed: list[str],
    failed: list[str],
    missing_evidence: list[str],
) -> None:
    requirements = _string_list(contract.get("algorithm_requirements"))
    if not requirements:
        passed.append("algorithm_requirements_not_configured")
        return

    if _ledger_artifact_exists(artifacts, "algorithm_decision"):
        passed.append("algorithm_decision")
    else:
        missing_evidence.append("algorithm_decision")
        failed.append("missing_algorithm_decision")


def _evaluate_cost_budget(
    contract: dict[str, Any],
    artifacts: list[dict[str, Any]],
    passed: list[str],
    failed: list[str],
    missing_evidence: list[str],
) -> None:
    budget = contract.get("cost_budget")
    if not isinstance(budget, dict) or not budget:
        passed.append("cost_budget_not_configured")
        return

    if _ledger_artifact_exists(artifacts, "cost_budget"):
        passed.append("cost_budget")
    else:
        missing_evidence.append("cost_budget")
        failed.append("missing_cost_budget")


def _evaluate_scope(
    contract: dict[str, Any],
    artifacts: list[dict[str, Any]],
    passed: list[str],
    failed: list[str],
    warnings: list[str],
    scope_violations: list[str],
) -> None:
    allowed_scope = [_normalize_path(value) for value in _string_list(contract.get("allowed_scope"))]
    if not allowed_scope:
        passed.append("allowed_scope_not_configured")
        return

    final_snapshot = _latest_snapshot(artifacts, "final")
    if final_snapshot is None:
        failed.append("scope_violation")
        warnings.append("final snapshot not recorded")
        return

    for changed in final_snapshot["metadata"].get("changed_files", []):
        path = _normalize_path(changed.get("path") if isinstance(changed, dict) else str(changed))
        if not _path_allowed(path, allowed_scope):
            scope_violations.append(path)
    if scope_violations:
        failed.append("scope_violation")
    else:
        passed.append("allowed_scope")


def _evaluate_open_risks(
    claims: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    passed: list[str],
    failed: list[str],
) -> None:
    open_risks = [
        claim
        for claim in claims
        if claim["metadata"].get("severity") in {"medium", "high"}
        and claim["status"] not in CLOSED_CLAIM_STATUSES
    ]
    if not open_risks:
        passed.append("open_risks")
        return

    has_accepted_decision = any(decision["status"] == "accepted" for decision in decisions)
    if has_accepted_decision:
        passed.append("risk_acceptance")
    else:
        failed.append("risk_acceptance_required")


def _ledger_haystack(
    artifacts: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
) -> str:
    parts: list[str] = []
    for artifact in artifacts:
        parts.extend(
            [
                artifact["artifact_type"],
                artifact["name"],
                json.dumps(artifact["metadata"], sort_keys=True),
            ]
        )
    for evidence_row in evidence_rows:
        parts.extend(
            [
                evidence_row["evidence_type"],
                evidence_row["content"],
                evidence_row["source_ref"] or "",
                json.dumps(evidence_row["metadata"], sort_keys=True),
            ]
        )
    return "\n".join(parts).lower()


def _latest_snapshot(artifacts: list[dict[str, Any]], phase: str) -> dict[str, Any] | None:
    snapshots = [
        artifact
        for artifact in artifacts
        if artifact["artifact_type"] == "git_diff"
        and artifact["metadata"].get("ledger_item_type") == "snapshot"
        and artifact["metadata"].get("phase") == phase
    ]
    return snapshots[-1] if snapshots else None


def _latest_evaluation(case_id: str) -> str | None:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT metadata_json
            FROM runs
            WHERE case_id = ? AND run_type = 'ledger_evaluation'
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (case_id,),
        ).fetchone()
    if row is None:
        return None

    status_value = loads_metadata(row["metadata_json"]).get("status")
    if isinstance(status_value, str) and status_value:
        return status_value
    return None


def _evaluation_status(failed: list[str]) -> str:
    for status_value in (
        "scope_violation",
        "needs_tests",
        "missing_algorithm_decision",
        "missing_cost_budget",
        "incomplete_evidence",
        "risk_acceptance_required",
    ):
        if status_value in failed:
            return status_value
    return "ready_for_review"


def _ledger_artifact_exists(artifacts: list[dict[str, Any]], item_type: str) -> bool:
    return any(
        artifact["metadata"].get("ledger_item_type") == item_type
        for artifact in artifacts
    )


def _insert_evaluation_run(
    case_id: str,
    status_value: str,
    passed: list[str],
    failed: list[str],
    warnings: list[str],
    missing_evidence: list[str],
    scope_violations: list[str],
) -> str:
    run_id = new_uuid()
    now = utc_now_iso()
    with connect() as connection:
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
                "ledger_evaluation",
                "completed",
                now,
                now,
                dumps_metadata(
                    {
                        "source": LEDGER_SOURCE,
                        "status": status_value,
                        "passed": passed,
                        "failed": failed,
                        "warnings": warnings,
                        "missing_evidence": missing_evidence,
                        "scope_violations": scope_violations,
                    }
                ),
                now,
                now,
            ),
        )
        connection.commit()
    return run_id


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.lstrip("/")


def _path_allowed(path: str, allowed_scope: list[str]) -> bool:
    return any(path == allowed or path.startswith(allowed.rstrip("/") + "/") for allowed in allowed_scope)
