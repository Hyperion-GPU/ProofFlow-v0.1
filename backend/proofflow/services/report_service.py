from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import hashlib
import json
import re

from proofflow.config import get_data_dir
from proofflow.db import connect, new_uuid, utc_now_iso
from proofflow.models.schemas import ReportExportRequest, ReportExportResponse
from proofflow.services.errors import NotFoundError
from proofflow.services.json_utils import dumps_metadata, loads_metadata


class ReportExportError(ValueError):
    """Raised when Proof Packet export cannot safely write a local report."""


def export_case_report(case_id: str, payload: ReportExportRequest) -> ReportExportResponse:
    if payload.format != "markdown":
        raise ReportExportError("only markdown export is supported")

    with connect() as connection:
        packet = _load_packet_data(connection, case_id)

    created_at = utc_now_iso()
    content = _render_markdown(packet, created_at)
    report_path = _next_report_path(case_id)
    _write_report(report_path, content)
    artifact_id = _record_report_artifact(case_id, report_path, content, created_at)

    return ReportExportResponse(
        case_id=case_id,
        artifact_id=artifact_id,
        format="markdown",
        path=str(report_path),
        filename=report_path.name,
        created_at=created_at,
        content=content,
    )


def _load_packet_data(connection: Any, case_id: str) -> dict[str, Any]:
    case = connection.execute(
        """
        SELECT id, title, case_type, status, summary, metadata_json, created_at, updated_at
        FROM cases
        WHERE id = ?
        """,
        (case_id,),
    ).fetchone()
    if case is None:
        raise NotFoundError(f"case not found: {case_id}")

    artifacts = connection.execute(
        """
        SELECT
            artifacts.id, artifacts.artifact_type, artifacts.uri, artifacts.name,
            artifacts.mime_type, artifacts.sha256, artifacts.size_bytes,
            artifacts.metadata_json, case_artifacts.role,
            artifacts.created_at, artifacts.updated_at
        FROM case_artifacts
        JOIN artifacts ON artifacts.id = case_artifacts.artifact_id
        WHERE case_artifacts.case_id = ?
        ORDER BY artifacts.created_at ASC, artifacts.id ASC
        """,
        (case_id,),
    ).fetchall()
    claims = connection.execute(
        """
        SELECT id, run_id, claim_text, claim_type, status, metadata_json, created_at, updated_at
        FROM claims
        WHERE case_id = ?
        ORDER BY created_at ASC, id ASC
        """,
        (case_id,),
    ).fetchall()
    evidence = connection.execute(
        """
        SELECT
            evidence.id, evidence.artifact_id, evidence.claim_id, evidence.evidence_type,
            evidence.content, evidence.source_ref, evidence.metadata_json,
            evidence.created_at, artifacts.name AS artifact_name,
            artifacts.uri AS artifact_uri,
            artifacts.metadata_json AS artifact_metadata_json
        FROM evidence
        LEFT JOIN artifacts ON artifacts.id = evidence.artifact_id
        WHERE evidence.case_id = ?
        ORDER BY evidence.created_at ASC, evidence.id ASC
        """,
        (case_id,),
    ).fetchall()
    actions = connection.execute(
        """
        SELECT
            id, action_type, status, title, reason, preview_json,
            result_json, undo_json, metadata_json, created_at, updated_at
        FROM actions
        WHERE case_id = ?
        ORDER BY created_at ASC, id ASC
        """,
        (case_id,),
    ).fetchall()
    decisions = connection.execute(
        """
        SELECT id, title, status, rationale, result, created_at, updated_at
        FROM decisions
        WHERE case_id = ?
        ORDER BY created_at ASC, id ASC
        """,
        (case_id,),
    ).fetchall()
    runs = connection.execute(
        """
        SELECT id, run_type, status, started_at, finished_at, metadata_json, created_at, updated_at
        FROM runs
        WHERE case_id = ?
        ORDER BY created_at ASC, id ASC
        """,
        (case_id,),
    ).fetchall()

    return {
        "case": case,
        "artifacts": artifacts,
        "claims": claims,
        "evidence": evidence,
        "actions": actions,
        "decisions": decisions,
        "runs": runs,
    }


def _render_markdown(packet: dict[str, Any], created_at: str) -> str:
    case = packet["case"]
    lines = [
        f"# Proof Packet: {_md(case['title'])}",
        "",
        f"Generated: `{created_at}`",
        "",
        "## Case Summary",
        "",
        f"- Case ID: `{case['id']}`",
        f"- Title: {_md(case['title'])}",
        f"- Workflow type: `{case['case_type']}`",
        f"- Status: `{case['status']}`",
        f"- Created: `{case['created_at']}`",
        f"- Updated: `{case['updated_at']}`",
        f"- Summary: {_md(case['summary'] or 'No summary recorded.')}",
        "",
    ]

    lines.extend(_render_artifacts(packet["artifacts"]))
    lines.extend(_render_untracked_policy(packet["case"], packet["artifacts"]))
    lines.extend(_render_claims_and_evidence(packet["claims"], packet["evidence"]))
    lines.extend(_render_actions(packet["actions"]))
    lines.extend(_render_decisions(packet["decisions"]))
    lines.extend(_render_runs(packet["runs"]))
    lines.extend(_render_remaining_risks(packet["claims"]))
    return "\n".join(lines).rstrip() + "\n"


def _render_artifacts(artifacts: list[Any]) -> list[str]:
    lines = ["## Artifacts", ""]
    if not artifacts:
        return lines + ["No artifacts recorded.", ""]

    for artifact in artifacts:
        metadata = loads_metadata(artifact["metadata_json"])
        path = metadata.get("path") or artifact["uri"]
        lines.extend(
            [
                f"- `{artifact['id']}` {_md(artifact['name'])}",
                f"  - Kind: `{artifact['artifact_type']}`; Role: `{artifact['role']}`",
                f"  - Path: `{path}`",
                f"  - SHA-256: `{artifact['sha256'] or 'not recorded'}`",
            ]
        )
    return lines + [""]


def _render_untracked_policy(case: Any, artifacts: list[Any]) -> list[str]:
    notes = _collect_untracked_policy_notes(case, artifacts)
    if not notes:
        return []

    lines = [
        "## AgentGuard Untracked Policy",
        "",
        (
            "AgentGuard omitted the following untracked file contents from the "
            "diff and Proof Packet. Only non-sensitive policy metadata is shown."
        ),
        "",
    ]
    for note in notes:
        lines.extend(
            [
                f"- `{_md(note['path'])}`",
                f"  - reason: `{_md(note['reason'])}`",
                f"  - truncated: `{str(note['truncated']).lower()}`",
                f"  - size_bytes: `{_metadata_value(note.get('size_bytes'))}`",
                f"  - cap_bytes: `{_metadata_value(note.get('cap_bytes'))}`",
            ]
        )
    return lines + [""]


def _render_claims_and_evidence(claims: list[Any], evidence_rows: list[Any]) -> list[str]:
    lines = ["## Claims & Evidence", ""]
    if not claims:
        return lines + ["No claims recorded.", ""]

    evidence_by_claim: dict[str, list[Any]] = {}
    for evidence in evidence_rows:
        evidence_by_claim.setdefault(evidence["claim_id"], []).append(evidence)

    for claim in claims:
        metadata = loads_metadata(claim["metadata_json"])
        severity = metadata.get("severity", "unknown")
        lines.extend(
            [
                f"### Claim: {_md(claim['claim_text'])}",
                "",
                f"- Claim ID: `{claim['id']}`",
                f"- Type: `{claim['claim_type']}`",
                f"- Status: `{claim['status']}`",
                f"- Severity: `{severity}`",
                "",
            ]
        )
        for evidence in evidence_by_claim.get(claim["id"], []):
            path = _evidence_artifact_path(evidence)
            lines.extend(
                [
                    f"- Evidence `{evidence['id']}` ({evidence['evidence_type']})",
                    f"  - Artifact: `{evidence['artifact_id'] or 'none'}` {_md(evidence['artifact_name'] or '')}",
                    f"  - Path: `{path}`",
                    f"  - Source ref: `{evidence['source_ref'] or 'not recorded'}`",
                    "",
                    *_quote_block(evidence["content"]),
                    "",
                ]
            )
    return lines


def _render_actions(actions: list[Any]) -> list[str]:
    lines = ["## Actions", ""]
    if not actions:
        return lines + ["No actions recorded.", ""]

    for action in actions:
        lines.extend(
            [
                f"- {_md(action['title'])}",
                f"  - Action ID: `{action['id']}`",
                f"  - Kind: `{action['action_type']}`",
                f"  - Status: `{action['status']}`",
                f"  - Reason: {_md(action['reason'])}",
                f"  - Preview: `{_compact_json(action['preview_json'])}`",
                f"  - Result: `{_compact_json(action['result_json'])}`",
                f"  - Undo: `{_compact_json(action['undo_json'])}`",
            ]
        )
    return lines + [""]


def _render_decisions(decisions: list[Any]) -> list[str]:
    lines = ["## Decisions", ""]
    if not decisions:
        return lines + ["No decisions recorded.", ""]

    for decision in decisions:
        lines.extend(
            [
                f"- {_md(decision['title'])}",
                f"  - Decision ID: `{decision['id']}`",
                f"  - Status: `{decision['status']}`",
                f"  - Rationale: {_md(decision['rationale'])}",
                f"  - Result: {_md(decision['result'])}",
            ]
        )
    return lines + [""]


def _render_runs(runs: list[Any]) -> list[str]:
    lines = ["## Runs & Test Results", ""]
    if not runs:
        return lines + ["No runs recorded.", ""]

    for run in runs:
        metadata = loads_metadata(run["metadata_json"])
        lines.extend(
            [
                f"- Run `{run['id']}`",
                f"  - Type: `{run['run_type']}`",
                f"  - Status: `{run['status']}`",
                f"  - Started: `{run['started_at']}`",
                f"  - Finished: `{run['finished_at'] or 'not recorded'}`",
                f"  - Test status: `{metadata.get('test_status', 'not recorded')}`",
                f"  - Test command: `{metadata.get('test_command', 'not recorded')}`",
                f"  - Risk level: `{metadata.get('risk_level', 'not recorded')}`",
            ]
        )
    return lines + [""]


def _render_remaining_risks(claims: list[Any]) -> list[str]:
    lines = ["## Remaining Risks", ""]
    risks = []
    closed_statuses = {"closed", "resolved", "accepted", "rejected"}
    for claim in claims:
        metadata = loads_metadata(claim["metadata_json"])
        severity = metadata.get("severity", "info")
        if severity != "info" and claim["status"] not in closed_statuses:
            risks.append((severity, claim["claim_text"]))

    if not risks:
        return lines + ["No non-info open risks recorded.", ""]

    for severity, text in risks:
        lines.append(f"- `{severity}` {_md(text)}")
    return lines + [""]


def _next_report_path(case_id: str) -> Path:
    output_dir = get_data_dir() / "proof_packets"
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_case_id = _sanitize_filename(case_id)
    base_path = output_dir / f"{safe_case_id}.md"
    if not base_path.exists():
        return base_path

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    candidate = output_dir / f"{safe_case_id}-{timestamp}.md"
    index = 1
    while candidate.exists():
        candidate = output_dir / f"{safe_case_id}-{timestamp}-{index}.md"
        index += 1
    return candidate


def _write_report(path: Path, content: str) -> None:
    try:
        path.write_text(content, encoding="utf-8")
    except OSError as error:
        raise ReportExportError(f"could not write proof packet: {error}") from error


def _record_report_artifact(
    case_id: str,
    report_path: Path,
    content: str,
    created_at: str,
) -> str:
    artifact_id = new_uuid()
    encoded = content.encode("utf-8")
    resolved_path = report_path.resolve()
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
                "proof_packet",
                resolved_path.as_uri(),
                report_path.name,
                "text/markdown",
                hashlib.sha256(encoded).hexdigest(),
                len(encoded),
                dumps_metadata(
                    {
                        "source": "proof_packet_export",
                        "path": str(resolved_path),
                        "format": "markdown",
                    }
                ),
                created_at,
                created_at,
            ),
        )
        connection.execute(
            """
            INSERT INTO case_artifacts (
                case_id, artifact_id, role, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (case_id, artifact_id, "reference", created_at, created_at),
        )
        connection.commit()
    return artifact_id


def _sanitize_filename(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip(".-")
    return sanitized or "proof-packet"


def _evidence_artifact_path(evidence: Any) -> str:
    metadata = loads_metadata(evidence["artifact_metadata_json"])
    path = metadata.get("path")
    if isinstance(path, str) and path:
        return path
    return evidence["artifact_uri"] or "not recorded"


def _collect_untracked_policy_notes(case: Any, artifacts: list[Any]) -> list[dict[str, Any]]:
    notes: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    case_metadata = loads_metadata(case["metadata_json"])
    _append_untracked_policy_notes(notes, seen, case_metadata.get("untracked_policy_notes"))

    for artifact in artifacts:
        metadata = loads_metadata(artifact["metadata_json"])
        _append_untracked_policy_notes(notes, seen, metadata.get("untracked_policy_notes"))

    return notes


def _append_untracked_policy_notes(
    notes: list[dict[str, Any]],
    seen: set[tuple[Any, ...]],
    raw_notes: Any,
) -> None:
    if not isinstance(raw_notes, list):
        return

    for raw_note in raw_notes:
        note = _sanitize_untracked_policy_note(raw_note)
        if note is None:
            continue
        key = (
            note["path"],
            note["reason"],
            note.get("size_bytes"),
            note.get("cap_bytes"),
            note["truncated"],
        )
        if key in seen:
            continue
        seen.add(key)
        notes.append(note)


def _sanitize_untracked_policy_note(raw_note: Any) -> dict[str, Any] | None:
    if not isinstance(raw_note, dict):
        return None

    path = raw_note.get("path")
    reason = raw_note.get("reason")
    if not isinstance(path, str) or not path:
        return None
    if not isinstance(reason, str) or not reason:
        return None

    note: dict[str, Any] = {
        "path": path,
        "reason": reason,
        "truncated": raw_note.get("truncated") is True,
    }
    size_bytes = raw_note.get("size_bytes")
    if isinstance(size_bytes, int) and size_bytes >= 0:
        note["size_bytes"] = size_bytes
    cap_bytes = raw_note.get("cap_bytes")
    if isinstance(cap_bytes, int) and cap_bytes >= 0:
        note["cap_bytes"] = cap_bytes
    return note


def _metadata_value(value: Any) -> str:
    if value is None:
        return "not recorded"
    return str(value)


def _quote_block(content: str) -> list[str]:
    snippet = (content or "").strip()
    if len(snippet) > 500:
        snippet = snippet[:497].rstrip() + "..."
    lines = snippet.splitlines() or ["No evidence content recorded."]
    return [f"> {line}" if line else ">" for line in lines]


def _compact_json(raw_json: str | None) -> str:
    if not raw_json:
        return "not recorded"
    try:
        decoded = json.loads(raw_json)
    except json.JSONDecodeError:
        return raw_json
    return json.dumps(decoded, sort_keys=True, separators=(",", ":"))


def _md(value: Any) -> str:
    text = str(value)
    return text.replace("\n", " ").strip()
