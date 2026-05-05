"""Policy gate owner decision gate types.

These types define the contract for requiring and binding an owner Decision
to a specific policy evaluation context. They are used by the decision
validator to determine whether execution may proceed.

This module is stateless and has no runtime dependencies (no DB, no API,
no side effects).
"""

from __future__ import annotations

from dataclasses import dataclass

from proofflow.services.policy_gate_service import PolicyCategory


@dataclass(frozen=True)
class PolicyGateDecisionRequirement:
    """Represents a pending owner decision requirement for a high-risk action.

    Created when a policy evaluation produces `require_decision`. The action
    cannot execute until an owner Decision is created and validated against
    this requirement.
    """

    action_id: str
    case_id: str
    policy_evaluation_id: str
    observation_id: str
    preview_hash: str
    categories: tuple[PolicyCategory, ...]
    reason: str
    remaining_risks: tuple[str, ...]
    required_at: str

    def __post_init__(self) -> None:
        """Normalize sequence fields so frozen instances stay deeply immutable."""
        object.__setattr__(self, "categories", tuple(self.categories))
        object.__setattr__(self, "remaining_risks", tuple(self.remaining_risks))


@dataclass(frozen=True)
class PolicyGateDecisionBinding:
    """Binds an owner Decision to a specific policy evaluation context.

    A binding is valid only when all context fields (action_id,
    policy_evaluation_id, preview_hash) match the original requirement.
    """

    decision_id: str
    action_id: str
    policy_evaluation_id: str
    preview_hash: str
    bound_at: str
    accepted: bool
    rationale: str
