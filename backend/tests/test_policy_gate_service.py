import json
from dataclasses import FrozenInstanceError

import pytest

from proofflow.services.policy_gate_service import (
    PolicyCategory,
    PolicyGateEvaluation,
    PolicyGateResult,
    PolicyOutcome,
    PolicySeverity,
    is_blocking_outcome,
    most_restrictive_outcome,
    outcome_precedence,
    requires_operator_decision,
)


def _policy_result(policy_id: str, outcome: PolicyOutcome) -> PolicyGateResult:
    return PolicyGateResult(
        policy_id=policy_id,
        policy_name=f"{policy_id} policy",
        category=PolicyCategory.BACKUP_RESTORE_TARGET_RISK,
        severity=PolicySeverity.MEDIUM,
        outcome=outcome,
        reason=f"{outcome.value} result for aggregation.",
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

    assert first.affected_paths == ()
    assert second.affected_paths == ()
    first_payload = first.to_dict()
    second_payload = second.to_dict()
    first_payload["affected_paths"].append("D:/proof/source")

    assert first.to_dict()["affected_paths"] == []
    assert second_payload["affected_paths"] == []
    assert first.to_dict()["redaction_status"] == "not_applicable"
    assert first.to_dict()["remaining_risks"] == []
    assert first.to_dict()["matched_surface"] is None
    assert first.to_dict()["related_decision_id"] is None


def test_policy_gate_result_collections_are_immutable_and_alias_safe():
    paths = ["D:/proof/source"]
    commands = ["managed_restore_to_new_location"]
    roots = ["D:/proof"]
    risks = ["Operator still needs to inspect restored files."]
    result = PolicyGateResult(
        policy_id="immutable-collections",
        policy_name="Immutable collections",
        category=PolicyCategory.BACKUP_RESTORE_TARGET_RISK,
        severity=PolicySeverity.MEDIUM,
        outcome=PolicyOutcome.WARN,
        reason="Collections should not mutate after construction.",
        affected_paths=paths,
        affected_commands=commands,
        allowed_roots_snapshot=roots,
        remaining_risks=risks,
    )

    assert result.affected_paths == ("D:/proof/source",)
    assert result.affected_commands == ("managed_restore_to_new_location",)
    assert result.allowed_roots_snapshot == ("D:/proof",)
    assert result.remaining_risks == ("Operator still needs to inspect restored files.",)

    paths.append("D:/proof/other")
    commands.append("unexpected_command")
    roots.append("D:/other")
    risks.append("Unexpected risk")

    assert result.affected_paths == ("D:/proof/source",)
    assert result.affected_commands == ("managed_restore_to_new_location",)
    assert result.allowed_roots_snapshot == ("D:/proof",)
    assert result.remaining_risks == ("Operator still needs to inspect restored files.",)

    payload = result.to_dict()
    payload["affected_paths"].append("D:/proof/from-payload")
    payload["remaining_risks"].append("Payload-only risk")

    assert result.affected_paths == ("D:/proof/source",)
    assert result.remaining_risks == ("Operator still needs to inspect restored files.",)

    with pytest.raises(FrozenInstanceError):
        result.affected_paths = ("D:/proof/reassigned",)


def test_empty_outcome_aggregation_fails_closed():
    assert most_restrictive_outcome([]) == PolicyOutcome.FAIL_CLOSED


def test_policy_gate_evaluation_empty_results_fail_closed():
    evaluation = PolicyGateEvaluation()

    assert evaluation.final_outcome == PolicyOutcome.FAIL_CLOSED
    assert evaluation.is_blocking
    assert not evaluation.requires_operator_decision
    assert not evaluation.has_warnings


def test_policy_gate_evaluation_aggregates_final_outcome():
    assert (
        PolicyGateEvaluation(
            results=[
                _policy_result("allow", PolicyOutcome.ALLOW),
                _policy_result("warn", PolicyOutcome.WARN),
            ]
        ).final_outcome
        == PolicyOutcome.WARN
    )
    assert (
        PolicyGateEvaluation(
            results=[
                _policy_result("warn", PolicyOutcome.WARN),
                _policy_result("decision", PolicyOutcome.REQUIRE_DECISION),
            ]
        ).final_outcome
        == PolicyOutcome.REQUIRE_DECISION
    )
    assert (
        PolicyGateEvaluation(
            results=[
                _policy_result("decision", PolicyOutcome.REQUIRE_DECISION),
                _policy_result("block", PolicyOutcome.BLOCK),
            ]
        ).final_outcome
        == PolicyOutcome.BLOCK
    )
    assert (
        PolicyGateEvaluation(
            results=[
                _policy_result("block", PolicyOutcome.BLOCK),
                _policy_result("fail", PolicyOutcome.FAIL_CLOSED),
            ]
        ).final_outcome
        == PolicyOutcome.FAIL_CLOSED
    )


def test_policy_gate_evaluation_flags_decision_blocking_and_warnings():
    decision = PolicyGateEvaluation(
        results=[_policy_result("decision", PolicyOutcome.REQUIRE_DECISION)]
    )
    block = PolicyGateEvaluation(results=[_policy_result("block", PolicyOutcome.BLOCK)])
    warn = PolicyGateEvaluation(results=[_policy_result("warn", PolicyOutcome.WARN)])

    assert decision.requires_operator_decision
    assert not decision.is_blocking
    assert block.is_blocking
    assert not block.requires_operator_decision
    assert warn.has_warnings
    assert not warn.is_blocking


def test_policy_gate_evaluation_serializes_to_json_safe_dict():
    evaluation = PolicyGateEvaluation(
        results=[
            _policy_result("allow", PolicyOutcome.ALLOW),
            _policy_result("warn", PolicyOutcome.WARN),
        ]
    )

    payload = evaluation.to_dict()
    json.dumps(payload)

    assert payload["final_outcome"] == "warn"
    assert payload["is_blocking"] is False
    assert payload["requires_operator_decision"] is False
    assert payload["has_warnings"] is True
    assert [result["outcome"] for result in payload["results"]] == ["allow", "warn"]


def test_policy_gate_evaluation_results_are_immutable_and_alias_safe():
    results = [_policy_result("allow", PolicyOutcome.ALLOW)]
    evaluation = PolicyGateEvaluation(results=results)

    assert evaluation.results == (results[0],)

    results.append(_policy_result("block", PolicyOutcome.BLOCK))
    assert evaluation.results == (results[0],)
    assert evaluation.final_outcome == PolicyOutcome.ALLOW

    payload = evaluation.to_dict()
    payload["results"].append(_policy_result("warn", PolicyOutcome.WARN).to_dict())
    payload["results"][0]["policy_id"] = "changed-in-payload"

    assert evaluation.results == (results[0],)
    assert evaluation.to_dict()["results"] == [results[0].to_dict()]

    with pytest.raises(FrozenInstanceError):
        evaluation.results = ()
