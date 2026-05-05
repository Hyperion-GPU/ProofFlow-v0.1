"""Tests for the policy gate owner decision gate types and validator."""

from __future__ import annotations

import inspect

import pytest

from proofflow.services.policy_gate_decision_gate import (
    PolicyGateDecisionBinding,
    PolicyGateDecisionRequirement,
)
from proofflow.services.policy_gate_decision_validator import (
    PolicyGateDecisionValidation,
    validate_decision_binding,
)
from proofflow.services.policy_gate_service import PolicyCategory


def _requirement(
    *,
    action_id: str = "action-1",
    case_id: str = "case-1",
    policy_evaluation_id: str = "eval-1",
    observation_id: str = "obs-1",
    preview_hash: str = "hash-abc",
    categories: tuple[PolicyCategory, ...] = (PolicyCategory.DESTRUCTIVE_LOCAL_OPERATION,),
    reason: str = "high-risk file move",
    remaining_risks: tuple[str, ...] = ("file cannot be recovered without backup",),
    required_at: str = "2026-05-05T00:00:00Z",
) -> PolicyGateDecisionRequirement:
    return PolicyGateDecisionRequirement(
        action_id=action_id,
        case_id=case_id,
        policy_evaluation_id=policy_evaluation_id,
        observation_id=observation_id,
        preview_hash=preview_hash,
        categories=categories,
        reason=reason,
        remaining_risks=remaining_risks,
        required_at=required_at,
    )


def _binding(
    *,
    decision_id: str = "decision-1",
    action_id: str = "action-1",
    policy_evaluation_id: str = "eval-1",
    preview_hash: str = "hash-abc",
    bound_at: str = "2026-05-05T00:01:00Z",
    accepted: bool = True,
    rationale: str = "Owner reviewed and approved",
) -> PolicyGateDecisionBinding:
    return PolicyGateDecisionBinding(
        decision_id=decision_id,
        action_id=action_id,
        policy_evaluation_id=policy_evaluation_id,
        preview_hash=preview_hash,
        bound_at=bound_at,
        accepted=accepted,
        rationale=rationale,
    )


class TestValidBindingAccepted:
    def test_matching_context_is_valid_and_accepted(self):
        requirement = _requirement()
        binding = _binding()

        result = validate_decision_binding(requirement, binding)

        assert result.valid is True
        assert result.accepted is True
        assert result.mismatch_reasons == ()
        assert result.requirement is requirement
        assert result.binding is binding


class TestActionIdMismatch:
    def test_different_action_id_is_invalid(self):
        requirement = _requirement(action_id="action-1")
        binding = _binding(action_id="action-other")

        result = validate_decision_binding(requirement, binding)

        assert result.valid is False
        assert result.accepted is False
        assert "action_id_mismatch" in result.mismatch_reasons


class TestPreviewHashMismatch:
    def test_different_preview_hash_is_invalid(self):
        requirement = _requirement(preview_hash="hash-abc")
        binding = _binding(preview_hash="hash-different")

        result = validate_decision_binding(requirement, binding)

        assert result.valid is False
        assert result.accepted is False
        assert "preview_hash_mismatch" in result.mismatch_reasons


class TestPolicyEvaluationIdMismatch:
    def test_different_evaluation_id_is_invalid(self):
        requirement = _requirement(policy_evaluation_id="eval-1")
        binding = _binding(policy_evaluation_id="eval-other")

        result = validate_decision_binding(requirement, binding)

        assert result.valid is False
        assert result.accepted is False
        assert "policy_evaluation_id_mismatch" in result.mismatch_reasons


class TestRejectedDecision:
    def test_rejected_binding_is_valid_but_not_accepted(self):
        requirement = _requirement()
        binding = _binding(accepted=False, rationale="Owner rejected: too risky")

        result = validate_decision_binding(requirement, binding)

        assert result.valid is True
        assert result.accepted is False
        assert result.mismatch_reasons == ()


class TestMissingBinding:
    def test_none_binding_is_invalid(self):
        requirement = _requirement()

        result = validate_decision_binding(requirement, None)

        assert result.valid is False
        assert result.accepted is False
        assert "no_decision_binding_provided" in result.mismatch_reasons
        assert result.binding is None


class TestMultipleMismatches:
    def test_all_mismatches_reported_together(self):
        requirement = _requirement(
            action_id="action-1",
            policy_evaluation_id="eval-1",
            preview_hash="hash-abc",
        )
        binding = _binding(
            action_id="action-wrong",
            policy_evaluation_id="eval-wrong",
            preview_hash="hash-wrong",
        )

        result = validate_decision_binding(requirement, binding)

        assert result.valid is False
        assert len(result.mismatch_reasons) == 3
        assert "action_id_mismatch" in result.mismatch_reasons
        assert "policy_evaluation_id_mismatch" in result.mismatch_reasons
        assert "preview_hash_mismatch" in result.mismatch_reasons


class TestImmutability:
    def test_requirement_is_frozen(self):
        requirement = _requirement()
        with pytest.raises(AttributeError):
            requirement.action_id = "mutated"  # type: ignore[misc]

    def test_binding_is_frozen(self):
        binding = _binding()
        with pytest.raises(AttributeError):
            binding.accepted = False  # type: ignore[misc]

    def test_validation_is_frozen(self):
        result = validate_decision_binding(_requirement(), _binding())
        with pytest.raises(AttributeError):
            result.valid = False  # type: ignore[misc]

    def test_requirement_normalizes_list_inputs_to_tuples(self):
        categories = [PolicyCategory.DESTRUCTIVE_LOCAL_OPERATION]
        remaining_risks = ["file cannot be recovered without backup"]
        requirement = _requirement(
            categories=categories,  # type: ignore[arg-type]
            remaining_risks=remaining_risks,  # type: ignore[arg-type]
        )

        assert isinstance(requirement.categories, tuple)
        assert isinstance(requirement.remaining_risks, tuple)

        categories.append(PolicyCategory.SECRET_ACCESS)
        remaining_risks.append("accidental data leakage")
        assert requirement.categories == (PolicyCategory.DESTRUCTIVE_LOCAL_OPERATION,)
        assert requirement.remaining_risks == ("file cannot be recovered without backup",)


class TestNoRuntimeImports:
    def test_decision_gate_module_does_not_import_runtime(self):
        import proofflow.services.policy_gate_decision_gate as mod

        source = inspect.getsource(mod)
        forbidden = [
            "proofflow.routers",
            "proofflow.db",
            "proofflow.migrations",
            "proofflow.services.action_service",
            "proofflow.services.backup_service",
            "proofflow.services.restore_service",
        ]
        for name in forbidden:
            assert name not in source, f"decision gate imports runtime module: {name}"

    def test_validator_module_does_not_import_runtime(self):
        import proofflow.services.policy_gate_decision_validator as mod

        source = inspect.getsource(mod)
        forbidden = [
            "proofflow.routers",
            "proofflow.db",
            "proofflow.migrations",
            "proofflow.services.action_service",
            "proofflow.services.backup_service",
            "proofflow.services.restore_service",
        ]
        for name in forbidden:
            assert name not in source, f"validator imports runtime module: {name}"
