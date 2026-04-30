import inspect
import json
from dataclasses import FrozenInstanceError

import pytest

import proofflow.services.policy_gate_dry_run_observation as observation_module
from proofflow.services.policy_gate_action_classifier import PolicyGateActionSurface
from proofflow.services.policy_gate_dry_run_context import PolicyGateDryRunContext
from proofflow.services.policy_gate_dry_run_observation import (
    PolicyGateDryRunObservation,
    create_policy_gate_dry_run_observation,
)
from proofflow.services.policy_gate_service import (
    PolicyCategory,
    PolicyGateEvaluation,
    PolicyGateResult,
    PolicyOutcome,
    PolicySeverity,
)


AUTHORITY_FIELDS = {
    "allow_execution",
    "block_execution",
    "blocked_execution",
    "final_outcome",
    "is_blocking",
    "requires_operator_decision",
}

RUNTIME_IMPORT_MARKERS = {
    "proofflow.routers",
    "proofflow.db",
    "proofflow.migrations",
    "proofflow.services.action_service",
    "proofflow.services.restore_service",
    "proofflow.services.report_service",
}


def _policy_result(policy_id: str, outcome: PolicyOutcome) -> PolicyGateResult:
    return PolicyGateResult(
        policy_id=policy_id,
        policy_name=f"{policy_id} policy",
        category=PolicyCategory.DESTRUCTIVE_LOCAL_OPERATION,
        severity=PolicySeverity.HIGH,
        outcome=outcome,
        reason=f"{outcome.value} result for dry-run observation.",
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


def test_high_risk_destructive_allow_observation_recommends_review():
    observation = create_policy_gate_dry_run_observation(
        PolicyGateActionSurface(
            action_type="delete_file",
            is_destructive=True,
            has_preview=True,
            has_undo=True,
        ),
        _evaluation(PolicyOutcome.ALLOW),
        _bound_context(),
        observation_id="observation-1",
    )

    payload = observation.to_dict()

    assert observation.observation_id == "observation-1"
    assert observation.would_have_outcome == PolicyOutcome.ALLOW
    assert observation.recommended_for_review is True
    assert payload["would_have_outcome"] == "allow"
    assert payload["recommended_for_review"] is True
    assert payload["classification"]["high_risk"] is True
    assert payload["dry_run"]["context_bound"] is True


def test_harmless_read_only_allow_observation_does_not_recommend_review():
    observation = create_policy_gate_dry_run_observation(
        PolicyGateActionSurface(
            action_type="read_status",
            action_category="read_only",
            has_preview=True,
            has_source_reference=True,
        ),
        _evaluation(PolicyOutcome.ALLOW),
        _bound_context(),
    )

    assert observation.would_have_outcome == PolicyOutcome.ALLOW
    assert observation.recommended_for_review is False
    assert observation.to_dict()["recommended_for_review"] is False


def test_harmless_surface_with_missing_context_fails_closed_and_recommends_review():
    observation = create_policy_gate_dry_run_observation(
        PolicyGateActionSurface(
            action_type="read_status",
            action_category="read_only",
            has_preview=True,
        ),
        _evaluation(PolicyOutcome.ALLOW),
        PolicyGateDryRunContext(
            action_id="action-1",
            preview_hash="preview-hash-1",
        ),
    )

    payload = observation.to_dict()

    assert observation.would_have_outcome == PolicyOutcome.FAIL_CLOSED
    assert observation.recommended_for_review is True
    assert payload["would_have_outcome"] == "fail_closed"
    assert payload["dry_run"]["missing_context"] == ["case_id"]


def test_artifact_missing_source_recommends_review_because_invariant_is_missing():
    observation = create_policy_gate_dry_run_observation(
        PolicyGateActionSurface(
            action_type="write_artifact",
            action_category="artifact",
            has_preview=True,
        ),
        _evaluation(PolicyOutcome.ALLOW),
        _bound_context(),
    )

    assert observation.would_have_outcome == PolicyOutcome.ALLOW
    assert observation.recommended_for_review is True
    assert observation.classification.missing_invariants == ("missing_source_reference",)


def test_code_workflow_missing_tests_recommends_review_because_invariant_is_missing():
    observation = create_policy_gate_dry_run_observation(
        PolicyGateActionSurface(
            action_type="code_patch",
            is_code_workflow=True,
            has_preview=True,
            has_source_reference=True,
        ),
        _evaluation(PolicyOutcome.ALLOW),
        _bound_context(),
    )

    assert observation.would_have_outcome == PolicyOutcome.ALLOW
    assert observation.recommended_for_review is True
    assert observation.classification.missing_invariants == ("missing_test_evidence",)


@pytest.mark.parametrize(
    "outcome",
    [
        PolicyOutcome.WARN,
        PolicyOutcome.REQUIRE_DECISION,
        PolicyOutcome.BLOCK,
        PolicyOutcome.FAIL_CLOSED,
    ],
)
def test_review_outcomes_recommend_review(outcome):
    observation = create_policy_gate_dry_run_observation(
        PolicyGateActionSurface(
            action_type="read_status",
            action_category="read_only",
            has_preview=True,
        ),
        _evaluation(outcome),
        _bound_context(),
    )

    assert observation.would_have_outcome == outcome
    assert observation.recommended_for_review is True
    assert observation.to_dict()["recommended_for_review"] is True


def test_context_mismatch_fails_closed_and_recommends_review():
    observation = create_policy_gate_dry_run_observation(
        PolicyGateActionSurface(
            action_type="read_status",
            action_category="read_only",
            has_preview=True,
        ),
        _evaluation(PolicyOutcome.ALLOW),
        PolicyGateDryRunContext(
            case_id="case-1",
            action_id="action-1",
            preview_hash="preview-hash-1",
            expected_action_id="action-2",
            expected_preview_hash="preview-hash-1",
        ),
    )

    payload = observation.to_dict()

    assert observation.would_have_outcome == PolicyOutcome.FAIL_CLOSED
    assert observation.recommended_for_review is True
    assert payload["dry_run"]["context_mismatches"] == ["action_id"]


def test_observation_remains_non_enforcing_observed_only():
    observation = create_policy_gate_dry_run_observation(
        PolicyGateActionSurface(action_type="read_status", has_preview=True),
        _evaluation(PolicyOutcome.ALLOW),
        _bound_context(),
    )
    payload = observation.to_dict()

    assert observation.non_enforcing is True
    assert observation.label == "observed_only"
    assert payload["non_enforcing"] is True
    assert payload["label"] == "observed_only"
    assert "approval" not in payload["label"]
    assert "approved" not in payload["label"]
    assert "block" not in payload["label"]


def test_observation_top_level_payload_has_no_execution_authority_fields():
    observation = create_policy_gate_dry_run_observation(
        PolicyGateActionSurface(action_type="read_status", has_preview=True),
        _evaluation(PolicyOutcome.ALLOW),
        _bound_context(),
    )
    payload = observation.to_dict()

    assert payload["would_have_outcome"] == "allow"
    assert "would_have_outcome" in payload
    assert not AUTHORITY_FIELDS.intersection(payload)
    assert payload["dry_run"]["evaluation"]["final_outcome"] == "allow"


def test_observation_serialization_is_json_safe_and_alias_safe():
    observation = create_policy_gate_dry_run_observation(
        PolicyGateActionSurface(
            action_type="restore_and_install",
            is_restore_related=True,
            affected_commands=["npm install"],
            has_preview=True,
        ),
        _evaluation(PolicyOutcome.REQUIRE_DECISION),
        _bound_context(),
        observation_id="observation-json",
    )

    payload = observation.to_dict()
    json.dumps(payload)

    payload["classification"]["categories"].append("mutated")
    payload["classification"]["missing_invariants"].append("mutated")
    payload["dry_run"]["context"]["case_id"] = "mutated-case"
    payload["dry_run"]["evaluation"]["results"][0]["policy_id"] = "mutated-policy"

    assert observation.observation_id == "observation-json"
    assert observation.classification.categories == (
        PolicyCategory.BACKUP_RESTORE_TARGET_RISK,
        PolicyCategory.PACKAGE_DEPENDENCY_MUTATION,
    )
    assert observation.classification.missing_invariants == ()
    assert observation.dry_run.context.case_id == "case-1"
    assert observation.dry_run.evaluation.results[0].policy_id == "require_decision"


def test_observation_is_frozen():
    observation = create_policy_gate_dry_run_observation(
        PolicyGateActionSurface(action_type="read_status", has_preview=True),
        _evaluation(PolicyOutcome.ALLOW),
        _bound_context(),
    )

    with pytest.raises(FrozenInstanceError):
        observation.observation_id = "mutated"


def test_observation_non_enforcing_label_and_review_are_not_constructor_fields():
    classification = create_policy_gate_dry_run_observation(
        PolicyGateActionSurface(action_type="read_status", has_preview=True),
        _evaluation(PolicyOutcome.ALLOW),
        _bound_context(),
    ).classification
    dry_run = create_policy_gate_dry_run_observation(
        PolicyGateActionSurface(action_type="read_status", has_preview=True),
        _evaluation(PolicyOutcome.ALLOW),
        _bound_context(),
    ).dry_run

    with pytest.raises(TypeError):
        PolicyGateDryRunObservation(  # type: ignore[call-arg]
            classification=classification,
            dry_run=dry_run,
            non_enforcing=False,
        )

    with pytest.raises(TypeError):
        PolicyGateDryRunObservation(  # type: ignore[call-arg]
            classification=classification,
            dry_run=dry_run,
            label="approved",
        )

    with pytest.raises(TypeError):
        PolicyGateDryRunObservation(  # type: ignore[call-arg]
            classification=classification,
            dry_run=dry_run,
            recommended_for_review=False,
        )


def test_observation_module_does_not_import_runtime_api_db_or_report_services():
    source = inspect.getsource(observation_module)

    for marker in RUNTIME_IMPORT_MARKERS:
        assert marker not in source

    assert "PolicyGateDryRunObservation" in vars(observation_module)
