from typing import Any

import json

from proofflow.db import connect
from proofflow.models.schemas import (
    ActionResponse,
    CaseDetailResponse,
    CasePacketArtifact,
    CasePacketClaim,
    CasePacketEvidence,
    CasePacketResponse,
    CasePacketRun,
    DecisionResponse,
    RiskLevel,
)
from proofflow.services.errors import NotFoundError
from proofflow.services.json_utils import loads_metadata

_VALID_RISKS: set[str] = {"low", "info", "medium", "high"}
_RISK_ORDER = {"low": 0, "info": 1, "medium": 2, "high": 3}
_CLOSED_CLAIM_STATUSES = {"closed", "resolved", "accepted", "rejected"}


def get_case_packet(case_id: str) -> CasePacketResponse:
    with connect() as connection:
        case_row = connection.execute(
            """
            SELECT id, title, case_type, status, summary, metadata_json, created_at, updated_at
            FROM cases
            WHERE id = ?
            """,
            (case_id,),
        ).fetchone()
        if case_row is None:
            raise NotFoundError(f"case not found: {case_id}")

        decision_count = connection.execute(
            "SELECT COUNT(*) FROM decisions WHERE case_id = ?",
            (case_id,),
        ).fetchone()[0]
        artifact_rows = connection.execute(
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
        claim_rows = connection.execute(
            """
            SELECT id, run_id, claim_text, claim_type, status, metadata_json, created_at, updated_at
            FROM claims
            WHERE case_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (case_id,),
        ).fetchall()
        evidence_rows = connection.execute(
            """
            SELECT
                evidence.id, evidence.artifact_id, evidence.claim_id, evidence.evidence_type,
                evidence.content, evidence.source_ref, evidence.created_at,
                artifacts.name AS artifact_name,
                artifacts.uri AS artifact_uri,
                artifacts.metadata_json AS artifact_metadata_json
            FROM evidence
            LEFT JOIN artifacts ON artifacts.id = evidence.artifact_id
            WHERE evidence.case_id = ?
            ORDER BY evidence.created_at ASC, evidence.id ASC
            """,
            (case_id,),
        ).fetchall()
        action_rows = connection.execute(
            """
            SELECT
                id, case_id, action_type, status, title, reason, preview_json,
                result_json, undo_json, metadata_json, created_at, updated_at
            FROM actions
            WHERE case_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (case_id,),
        ).fetchall()
        decision_rows = connection.execute(
            """
            SELECT id, case_id, title, status, rationale, result, created_at, updated_at
            FROM decisions
            WHERE case_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (case_id,),
        ).fetchall()
        run_rows = connection.execute(
            """
            SELECT id, run_type, status, started_at, finished_at, metadata_json, created_at, updated_at
            FROM runs
            WHERE case_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (case_id,),
        ).fetchall()

    case_metadata = loads_metadata(case_row["metadata_json"])
    case = CaseDetailResponse(
        id=case_row["id"],
        title=case_row["title"],
        kind=case_row["case_type"],
        status=case_row["status"],
        summary=case_row["summary"],
        metadata=case_metadata,
        created_at=case_row["created_at"],
        updated_at=case_row["updated_at"],
        decision_count=decision_count,
    )
    evidence_by_claim = _group_evidence_by_claim(evidence_rows)
    claims = [_claim_from_row(row, evidence_by_claim.get(row["id"], [])) for row in claim_rows]

    return CasePacketResponse(
        case=case,
        risk_level=_derive_risk_level(case_metadata, claims),
        artifacts=[_artifact_from_row(row) for row in artifact_rows],
        claims=claims,
        actions=[_action_from_row(row) for row in action_rows],
        decisions=[_decision_from_row(row) for row in decision_rows],
        runs=[_run_from_row(row) for row in run_rows],
    )


def _artifact_from_row(row: Any) -> CasePacketArtifact:
    metadata = loads_metadata(row["metadata_json"])
    path = metadata.get("path")
    if not isinstance(path, str) or not path:
        path = row["uri"]
    return CasePacketArtifact(
        id=row["id"],
        kind=row["artifact_type"],
        role=row["role"],
        name=row["name"],
        uri=row["uri"],
        path=path,
        mime_type=row["mime_type"],
        sha256=row["sha256"],
        size_bytes=row["size_bytes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _group_evidence_by_claim(rows: list[Any]) -> dict[str, list[CasePacketEvidence]]:
    grouped: dict[str, list[CasePacketEvidence]] = {}
    for row in rows:
        evidence = _evidence_from_row(row)
        if evidence.claim_id is None:
            continue
        grouped.setdefault(evidence.claim_id, []).append(evidence)
    return grouped


def _evidence_from_row(row: Any) -> CasePacketEvidence:
    artifact_path = None
    artifact_metadata = loads_metadata(row["artifact_metadata_json"])
    metadata_path = artifact_metadata.get("path")
    if isinstance(metadata_path, str) and metadata_path:
        artifact_path = metadata_path
    elif row["artifact_uri"]:
        artifact_path = row["artifact_uri"]

    return CasePacketEvidence(
        id=row["id"],
        artifact_id=row["artifact_id"],
        claim_id=row["claim_id"],
        evidence_type=row["evidence_type"],
        content=row["content"] or "",
        source_ref=row["source_ref"],
        artifact_name=row["artifact_name"],
        artifact_path=artifact_path,
        created_at=row["created_at"],
    )


def _claim_from_row(row: Any, evidence: list[CasePacketEvidence]) -> CasePacketClaim:
    metadata = loads_metadata(row["metadata_json"])
    return CasePacketClaim(
        id=row["id"],
        run_id=row["run_id"],
        claim_text=row["claim_text"],
        claim_type=row["claim_type"],
        status=row["status"],
        severity=_normalize_risk(metadata.get("severity"), fallback="info"),
        evidence=evidence,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _action_from_row(row: Any) -> ActionResponse:
    return ActionResponse(
        id=row["id"],
        case_id=row["case_id"],
        kind=row["action_type"],
        status=row["status"],
        title=row["title"],
        reason=row["reason"],
        preview=loads_metadata(row["preview_json"]),
        result=_loads_optional_json(row["result_json"]),
        undo=_loads_optional_json(row["undo_json"]),
        metadata=loads_metadata(row["metadata_json"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _decision_from_row(row: Any) -> DecisionResponse:
    return DecisionResponse(
        id=row["id"],
        case_id=row["case_id"],
        title=row["title"],
        status=row["status"],
        rationale=row["rationale"],
        result=row["result"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _run_from_row(row: Any) -> CasePacketRun:
    return CasePacketRun(
        id=row["id"],
        run_type=row["run_type"],
        status=row["status"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        metadata=loads_metadata(row["metadata_json"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _derive_risk_level(case_metadata: dict[str, Any], claims: list[CasePacketClaim]) -> RiskLevel:
    metadata_risk = _normalize_risk(case_metadata.get("risk_level"), fallback=None)
    if metadata_risk is not None:
        return metadata_risk

    highest = "low"
    for claim in claims:
        if claim.severity == "info" or claim.status in _CLOSED_CLAIM_STATUSES:
            continue
        if _RISK_ORDER[claim.severity] > _RISK_ORDER[highest]:
            highest = claim.severity
    return highest  # type: ignore[return-value]


def _normalize_risk(value: Any, fallback: RiskLevel | None) -> RiskLevel | None:
    if isinstance(value, str) and value in _VALID_RISKS:
        return value  # type: ignore[return-value]
    return fallback


def _loads_optional_json(raw_json: str | None) -> dict[str, Any] | None:
    if not raw_json:
        return None
    try:
        decoded = json.loads(raw_json)
    except json.JSONDecodeError:
        return None
    if isinstance(decoded, dict):
        return decoded
    return None
