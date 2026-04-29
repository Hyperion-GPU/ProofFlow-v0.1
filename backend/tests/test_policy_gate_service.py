import json

from proofflow.services.policy_gate_service import (
    PolicyCategory,
    PolicyGateResult,
    PolicyOutcome,
    PolicySeverity,
    is_blocking_outcome,
    most_restrictive_outcome,
    outcome_precedence,
    requires_operator_decision,
)


def test_outcome_precedence_orders_policy_outcomes():
    ordered = [
        PolicyOutcome.ALLOW,
        PolicyOutcome.WARN,
        PolicyOutcome.REQUIRE_DECISION,
        PolicyOutcome.BLOCK,
        PolicyOutcome.FAIL_CLOSED,
    ]

    assert [outcome_precedence(outcome) for outcome in ordered] == [0, 1, 2, 3, 4]
    assert most_restrictive_outcome([PolicyOutcome.ALLOW, PolicyOutcome.WARN]) == PolicyOutcome.WARN
    assert (
        most_restrictive_outcome([PolicyOutcome.REQUIRE_DECISION, PolicyOutcome.BLOCK])
        == PolicyOutcome.BLOCK
    )
    assert (
        most_restrictive_outcome([PolicyOutcome.BLOCK, PolicyOutcome.FAIL_CLOSED])
        == PolicyOutcome.FAIL_CLOSED
    )


def test_blocking_and_decision_helpers_keep_meanings_separate():
    assert is_blocking_outcome(PolicyOutcome.BLOCK)
    assert is_blocking_outcome(PolicyOutcome.FAIL_CLOSED)

    assert not is_blocking_outcome(PolicyOutcome.ALLOW)
    assert not is_blocking_outcome(PolicyOutcome.WARN)
    assert not is_blocking_outcome(PolicyOutcome.REQUIRE_DECISION)

    assert requires_operator_decision(PolicyOutcome.REQUIRE_DECISION)
    assert not requires_operator_decision(PolicyOutcome.BLOCK)
    assert not requires_operator_decision(PolicyOutcome.FAIL_CLOSED)


def test_policy_gate_result_serializes_to_json_safe_dict():
    result = PolicyGateResult(
        policy_id="restore-target-review",
        policy_name="Restore target review",
        category=PolicyCategory.BACKUP_RESTORE_TARGET_RISK,
        severity=PolicySeverity.HIGH,
        outcome=PolicyOutcome.REQUIRE_DECISION,
        reason="Restore target requires explicit operator review.",
        matched_surface="restore_target",
        redaction_status="redacted",
        affected_paths=["D:/proof/restore/proofflow.db", "D:/proof/restore/data"],
        affected_commands=["managed_restore_to_new_location"],
        allowed_roots_snapshot=["D:/proof/restore"],
        related_case_id="case-1",
        related_action_id="action-1",
        related_decision_id="decision-1",
        related_evidence_id="evidence-1",
        transparency_event_id="event-1",
        remaining_risks=["Inspection restore does not prove live restore safety."],
    )

    payload = result.to_dict()
    json.dumps(payload)

    assert payload["category"] == "backup_restore_target_risk"
    assert payload["severity"] == "high"
    assert payload["outcome"] == "require_decision"
    assert payload["affected_paths"] == ["D:/proof/restore/proofflow.db", "D:/proof/restore/data"]
    assert payload["affected_commands"] == ["managed_restore_to_new_location"]
    assert payload["related_case_id"] == "case-1"
    assert payload["remaining_risks"] == ["Inspection restore does not prove live restore safety."]


def test_policy_gate_result_safe_defaults_are_independent_and_explicit():
    first = PolicyGateResult(
        policy_id="default-1",
        policy_name="Default result one",
        category=PolicyCategory.FILESYSTEM_ESCAPE,
        severity=PolicySeverity.INFO,
        outcome=PolicyOutcome.ALLOW,
        reason="No high-risk surface matched.",
    )
    second = PolicyGateResult(
        policy_id="default-2",
        policy_name="Default result two",
        category=PolicyCategory.SECRET_ACCESS,
        severity=PolicySeverity.LOW,
        outcome=PolicyOutcome.WARN,
        reason="Reviewable surface matched.",
    )

    first.affected_paths.append("D:/proof/source")

    assert second.affected_paths == []
    assert first.to_dict()["redaction_status"] == "not_applicable"
    assert first.to_dict()["remaining_risks"] == []
    assert first.to_dict()["matched_surface"] is None
    assert first.to_dict()["related_decision_id"] is None


def test_empty_outcome_aggregation_fails_closed():
    assert most_restrictive_outcome([]) == PolicyOutcome.FAIL_CLOSED
