"""Policy gate decision binding validator.

Pure validation logic that determines whether an owner Decision binding
satisfies a policy gate decision requirement. No DB, no API, no side effects.
"""

from __future__ import annotations

from dataclasses import dataclass

from proofflow.services.policy_gate_decision_gate import (
    PolicyGateDecisionBinding,
    PolicyGateDecisionRequirement,
)


@dataclass(frozen=True)
class PolicyGateDecisionValidation:
    """Result of validating a Decision binding against a requirement.

    - valid: all context fields match (action_id, evaluation_id, preview_hash)
    - accepted: the Decision was accepted (not rejected)
    - mismatch_reasons: tuple of human-readable reasons for any mismatches
    """

    valid: bool
    accepted: bool
    mismatch_reasons: tuple[str, ...]
    requirement: PolicyGateDecisionRequirement
    binding: PolicyGateDecisionBinding | None


def validate_decision_binding(
    requirement: PolicyGateDecisionRequirement,
    binding: PolicyGateDecisionBinding | None,
) -> PolicyGateDecisionValidation:
    """Validate that a Decision binding satisfies the requirement.

    Returns invalid if:
    - binding is None (no decision provided)
    - action_id mismatch
    - policy_evaluation_id mismatch
    - preview_hash mismatch (action was modified after observation)

    Returns valid but not accepted if the decision was rejected.
    """
    if binding is None:
        return PolicyGateDecisionValidation(
            valid=False,
            accepted=False,
            mismatch_reasons=("no_decision_binding_provided",),
            requirement=requirement,
            binding=None,
        )

    mismatches: list[str] = []

    if binding.action_id != requirement.action_id:
        mismatches.append("action_id_mismatch")

    if binding.policy_evaluation_id != requirement.policy_evaluation_id:
        mismatches.append("policy_evaluation_id_mismatch")

    if binding.preview_hash != requirement.preview_hash:
        mismatches.append("preview_hash_mismatch")

    if mismatches:
        return PolicyGateDecisionValidation(
            valid=False,
            accepted=False,
            mismatch_reasons=tuple(mismatches),
            requirement=requirement,
            binding=binding,
        )

    return PolicyGateDecisionValidation(
        valid=True,
        accepted=binding.accepted,
        mismatch_reasons=(),
        requirement=requirement,
        binding=binding,
    )
