import json
from dataclasses import FrozenInstanceError

import pytest

from proofflow.services.policy_gate_dry_run_context import (
    PolicyGateDryRunContext,
    bind_dry_run_context,
)
from proofflow.services.policy_gate_service import (
    PolicyCategory,
    PolicyGateEvaluation,
    PolicyGateResult,
    PolicyOutcome,
    PolicySeverity,
)


def _policy_result(policy_id: str, outcome: PolicyOutcome) -> PolicyGateResult:
    return PolicyGateResult(
        policy_id=policy_id,
        policy_name=f"{policy_id} policy",
        category=PolicyCategory.DESTRUCTIVE_LOCAL_OPERATION,
        severity=PolicySeverity.HIGH,
        outcome=outcome,
        reason=f"{outcome.value} result for context-bound dry-run evaluation.",
    )


def _evaluation(outcome: PolicyOutcome) -> PolicyGateEvaluation:
    return PolicyGateEvaluation(results=[_policy_result(outcome.value, outcome)])


def _bound_context() -> PolicyGateDryRunContext:
    return PolicyGateDryRunContext(
        case_id="case-1",
        action_id="action-1",
        preview_hash="preview-hash-1",
        policy_evaluation_id="policy-eval-1",
        expected_action_id="action-1",
        expected_preview_hash="preview-hash-1",
    )


def test_context_bound_allow_remains_allow():
    dry_run = bind_dry_run_context(_evaluation(PolicyOutcome.ALLOW), _bound_context())

    assert dry_run.context_bound
    assert dry_run.missing_context == ()
    assert dry_run.context_mismatches == ()
    assert dry_run.would_have_outcome == PolicyOutcome.ALLOW
    assert dry_run.to_dict()["would_have_outcome"] == "allow"


@pytest.mark.parametrize(
    "outcome",
    [PolicyOutcome.WARN, PolicyOutcome.REQUIRE_DECISION],
)
def test_context_bound_review_outcomes_preserve_original_outcome(outcome):
    dry_run = bind_dry_run_context(_evaluation(outcome), _bound_context())

    assert dry_run.context_bound
    assert dry_run.would_have_outcome == outcome


def test_context_bound_block_remains_block():
    dry_run = bind_dry_run_context(_evaluation(PolicyOutcome.BLOCK), _bound_context())

    assert dry_run.context_bound
    assert dry_run.would_have_outcome == PolicyOutcome.BLOCK


def test_context_bound_empty_evaluation_fails_closed():
    dry_run = bind_dry_run_context(PolicyGateEvaluation(), _bound_context())

    assert dry_run.context_bound
    assert dry_run.would_have_outcome == PolicyOutcome.FAIL_CLOSED


@pytest.mark.parametrize(
    ("context", "missing_key"),
    [
        (
            PolicyGateDryRunContext(
                action_id="action-1",
                preview_hash="preview-hash-1",
            ),
            "case_id",
        ),
        (
            PolicyGateDryRunContext(
                case_id="case-1",
                preview_hash="preview-hash-1",
            ),
            "action_id",
        ),
        (
            PolicyGateDryRunContext(
                case_id="case-1",
                action_id="action-1",
            ),
            "preview_hash",
        ),
    ],
)
def test_missing_context_fails_closed(context, missing_key):
    dry_run = bind_dry_run_context(_evaluation(PolicyOutcome.ALLOW), context)

    payload = dry_run.to_dict()

    assert not dry_run.context_bound
    assert dry_run.would_have_outcome == PolicyOutcome.FAIL_CLOSED
    assert dry_run.missing_context == (missing_key,)
    assert payload["would_have_outcome"] == "fail_closed"
    assert payload["missing_context"] == [missing_key]


@pytest.mark.parametrize(
    ("context", "mismatch_key"),
    [
        (
            PolicyGateDryRunContext(
                case_id="case-1",
                action_id="action-1",
                preview_hash="preview-hash-1",
                expected_action_id="action-2",
                expected_preview_hash="preview-hash-1",
            ),
            "action_id",
        ),
        (
            PolicyGateDryRunContext(
                case_id="case-1",
                action_id="action-1",
                preview_hash="preview-hash-1",
                expected_action_id="action-1",
                expected_preview_hash="preview-hash-2",
            ),
            "preview_hash",
        ),
    ],
)
def test_context_mismatch_fails_closed(context, mismatch_key):
    dry_run = bind_dry_run_context(_evaluation(PolicyOutcome.ALLOW), context)

    payload = dry_run.to_dict()

    assert not dry_run.context_bound
    assert dry_run.missing_context == ()
    assert dry_run.context_mismatches == (mismatch_key,)
    assert dry_run.would_have_outcome == PolicyOutcome.FAIL_CLOSED
    assert payload["context_mismatches"] == [mismatch_key]
    assert payload["would_have_outcome"] == "fail_closed"


def test_context_bound_dry_run_remains_non_enforcing_observed_only():
    dry_run = bind_dry_run_context(_evaluation(PolicyOutcome.ALLOW), _bound_context())
    payload = dry_run.to_dict()

    assert dry_run.non_enforcing is True
    assert dry_run.label == "observed_only"
    assert payload["non_enforcing"] is True
    assert payload["label"] == "observed_only"
    assert "approval" not in payload["label"]
    assert "approved" not in payload["label"]


def test_context_bound_dry_run_does_not_serialize_execution_authority_fields():
    dry_run = bind_dry_run_context(_evaluation(PolicyOutcome.ALLOW), _bound_context())
    payload = dry_run.to_dict()

    assert "allow_execution" not in payload
    assert "block_execution" not in payload
    assert "blocked_execution" not in payload
    assert "final_outcome" not in payload


def test_context_bound_dry_run_serialization_is_json_safe_and_alias_safe():
    dry_run = bind_dry_run_context(
        _evaluation(PolicyOutcome.ALLOW),
        PolicyGateDryRunContext(
            case_id="case-1",
            action_id="action-1",
            preview_hash="preview-hash-1",
            expected_action_id="action-2",
            expected_preview_hash="preview-hash-2",
        ),
    )

    payload = dry_run.to_dict()
    json.dumps(payload)

    assert payload["context_bound"] is False
    assert payload["context_mismatches"] == ["action_id", "preview_hash"]
    assert payload["context"]["case_id"] == "case-1"
    assert payload["evaluation"]["final_outcome"] == "allow"

    payload["context_mismatches"].append("mutated")
    payload["context"]["case_id"] = "mutated-case"
    payload["evaluation"]["results"][0]["policy_id"] = "mutated-policy"

    assert dry_run.context_mismatches == ("action_id", "preview_hash")
    assert dry_run.context.case_id == "case-1"
    assert dry_run.evaluation.results[0].policy_id == "allow"


def test_context_bound_dry_run_is_frozen():
    dry_run = bind_dry_run_context(PolicyGateEvaluation(), _bound_context())

    with pytest.raises(FrozenInstanceError):
        dry_run.context = PolicyGateDryRunContext()
