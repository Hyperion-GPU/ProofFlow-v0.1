"""Non-blocking dry-run policy gate observation at the pre-execution boundary.

This module is called from action_service.execute_action() to observe high-risk
actions before execution. It NEVER blocks execution and NEVER raises exceptions
to the caller.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

from proofflow.db import connect, new_uuid, utc_now_iso
from proofflow.services.json_utils import dumps_metadata, loads_metadata
from proofflow.services.policy_gate_action_classifier import (
    classify_policy_gate_action,
)
from proofflow.services.policy_gate_action_snapshot import (
    PolicyGateActionSnapshot,
    action_snapshot_to_surface,
    stable_preview_hash,
)
from proofflow.services.policy_gate_dry_run_pipeline import (
    evaluate_dry_run_pipeline,
)
from proofflow.services.policy_gate_service import (
    PolicyCategory,
    PolicyGateEvaluation,
    PolicyGateResult,
    PolicyOutcome,
    PolicySeverity,
)

logger = logging.getLogger(__name__)


def observe_pre_execution(action_row: sqlite3.Row) -> None:
    """Non-blocking dry-run observation at the pre-execution boundary.

    This function NEVER raises. On any error it logs a warning and returns.
    It does NOT block execution. It does NOT modify the action row.
    """
    try:
        _observe_inner(action_row)
    except Exception:
        logger.warning(
            "policy_gate_runtime_observer: observation failed (fail-open), "
            "action execution will proceed",
            exc_info=True,
        )


def _observe_inner(action_row: sqlite3.Row) -> None:
    action_id = action_row["id"]
    case_id = action_row["case_id"]
    action_type = action_row["action_type"]
    preview_json = action_row["preview_json"]
    metadata_json = action_row["metadata_json"]
    undo_json = action_row["undo_json"]

    preview = _safe_loads(preview_json)
    metadata = _safe_loads(metadata_json)
    undo = _safe_loads(undo_json)

    snapshot = PolicyGateActionSnapshot(
        action_type=action_type,
        case_id=case_id,
        action_id=action_id,
        preview=preview if preview else None,
        metadata=metadata if metadata else None,
        undo=undo if undo else None,
    )

    surface = action_snapshot_to_surface(snapshot)
    classification = classify_policy_gate_action(surface)

    if not classification.high_risk:
        return

    results = tuple(
        PolicyGateResult(
            policy_id=f"dry-run-observe-{category.value}",
            policy_name=f"Dry-run observation: {category.value}",
            category=category,
            severity=PolicySeverity.MEDIUM,
            outcome=PolicyOutcome.WARN,
            reason=f"high-risk category observed at pre-execution: {category.value}",
            matched_surface=action_type,
            related_case_id=case_id,
            related_action_id=action_id,
        )
        for category in classification.categories
    )

    evaluation = PolicyGateEvaluation(results=results)

    pipeline_id = new_uuid()
    observation_id = new_uuid()
    preview_hash = stable_preview_hash(snapshot.preview)

    pipeline_result = evaluate_dry_run_pipeline(
        snapshot,
        evaluation,
        expected_action_id=action_id,
        expected_preview_hash=preview_hash,
        pipeline_id=pipeline_id,
        observation_id=observation_id,
    )

    _record_evidence(
        case_id=case_id,
        action_id=action_id,
        pipeline_id=pipeline_id,
        observation_id=observation_id,
        pipeline_result_dict=pipeline_result.to_dict(),
    )


def _record_evidence(
    *,
    case_id: str,
    action_id: str,
    pipeline_id: str,
    observation_id: str,
    pipeline_result_dict: dict[str, Any],
) -> None:
    now = utc_now_iso()
    content = json.dumps(pipeline_result_dict, ensure_ascii=False)
    metadata = dumps_metadata(
        {
            "source": "policy_gate_runtime_observer",
            "pipeline_id": pipeline_id,
            "observation_id": observation_id,
            "non_enforcing": True,
            "high_risk": True,
        }
    )

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
                new_uuid(),
                case_id,
                None,
                None,
                "policy_gate_dry_run_observation",
                content,
                action_id,
                metadata,
                now,
                now,
            ),
        )
        connection.commit()


def _safe_loads(value: str | None) -> dict[str, Any] | None:
    if not value:
        return None
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
        return None
    except (json.JSONDecodeError, TypeError):
        return None
