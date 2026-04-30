import json
from dataclasses import FrozenInstanceError

import pytest

from proofflow.services.policy_gate_dry_run_service import (
    PolicyGateDryRunEvaluation,
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
        reason=f"{outcome.value} result for dry-run evaluation.",
    )


def test_dry_run_reports_block_as_would_have_outcome():
    dry_run = PolicyGateDryRunEvaluation(
        evaluation=PolicyGateEvaluation(
            results=[_policy_result("block", PolicyOutcome.BLOCK)]
        )
    )

    assert dry_run.would_have_outcome == PolicyOutcome.BLOCK
    assert dry_run.to_dict()["would_have_outcome"] == "block"


@pytest.mark.parametrize(
    "caller_outcome",
    [PolicyOutcome.ALLOW, PolicyOutcome.WARN],
)
def test_dry_run_caller_cannot_downgrade_fail_closed(caller_outcome):
    dry_run = PolicyGateDryRunEvaluation(
        evaluation=PolicyGateEvaluation(
            results=[_policy_result("fail", PolicyOutcome.FAIL_CLOSED)],
            final_outcome=caller_outcome,
        )
    )

    assert dry_run.would_have_outcome == PolicyOutcome.FAIL_CLOSED
    assert dry_run.to_dict()["would_have_outcome"] == "fail_closed"


def test_dry_run_empty_evaluation_fails_closed():
    dry_run = PolicyGateDryRunEvaluation(evaluation=PolicyGateEvaluation())

    assert dry_run.would_have_outcome == PolicyOutcome.FAIL_CLOSED
    assert dry_run.to_dict()["would_have_outcome"] == "fail_closed"


def test_dry_run_is_always_non_enforcing_and_observed_only():
    dry_run = PolicyGateDryRunEvaluation(
        evaluation=PolicyGateEvaluation(
            results=[_policy_result("allow", PolicyOutcome.ALLOW)]
        )
    )

    payload = dry_run.to_dict()

    assert dry_run.non_enforcing is True
    assert dry_run.label == "observed_only"
    assert payload["non_enforcing"] is True
    assert payload["label"] == "observed_only"
    assert "approval" not in payload["label"]
    assert "approved" not in payload["label"]


def test_dry_run_does_not_serialize_execution_authority_fields():
    dry_run = PolicyGateDryRunEvaluation(
        evaluation=PolicyGateEvaluation(
            results=[_policy_result("allow", PolicyOutcome.ALLOW)]
        )
    )

    payload = dry_run.to_dict()

    assert "allow_execution" not in payload
    assert "block_execution" not in payload
    assert "blocked_execution" not in payload
    assert "final_outcome" not in payload
    assert payload["evaluation"]["final_outcome"] == "allow"


def test_dry_run_records_missing_context_without_changing_outcome_semantics():
    missing_context = ["case_id", "preview_hash"]
    dry_run = PolicyGateDryRunEvaluation(
        evaluation=PolicyGateEvaluation(
            results=[_policy_result("warn", PolicyOutcome.WARN)]
        ),
        missing_context=missing_context,
    )

    assert dry_run.missing_context == ("case_id", "preview_hash")
    assert dry_run.would_have_outcome == PolicyOutcome.WARN
    assert dry_run.to_dict()["missing_context"] == ["case_id", "preview_hash"]

    missing_context.append("action_id")

    assert dry_run.missing_context == ("case_id", "preview_hash")


def test_dry_run_serialization_is_json_safe_and_alias_safe():
    dry_run = PolicyGateDryRunEvaluation(
        evaluation=PolicyGateEvaluation(
            results=[
                _policy_result("allow", PolicyOutcome.ALLOW),
                _policy_result("decision", PolicyOutcome.REQUIRE_DECISION),
            ]
        ),
        missing_context=["preview_hash"],
    )

    payload = dry_run.to_dict()
    json.dumps(payload)

    payload["missing_context"].append("mutated")
    payload["evaluation"]["results"][0]["policy_id"] = "mutated-policy"

    assert dry_run.missing_context == ("preview_hash",)
    assert dry_run.evaluation.results[0].policy_id == "allow"
    assert dry_run.to_dict()["missing_context"] == ["preview_hash"]


def test_dry_run_non_enforcing_and_label_are_not_constructor_authority_fields():
    evaluation = PolicyGateEvaluation(
        results=[_policy_result("allow", PolicyOutcome.ALLOW)]
    )

    with pytest.raises(TypeError):
        PolicyGateDryRunEvaluation(  # type: ignore[call-arg]
            evaluation=evaluation,
            non_enforcing=False,
        )

    with pytest.raises(TypeError):
        PolicyGateDryRunEvaluation(  # type: ignore[call-arg]
            evaluation=evaluation,
            label="approved",
        )


def test_dry_run_evaluation_is_frozen():
    dry_run = PolicyGateDryRunEvaluation(evaluation=PolicyGateEvaluation())

    with pytest.raises(FrozenInstanceError):
        dry_run.missing_context = ("case_id",)
