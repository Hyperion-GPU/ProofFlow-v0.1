from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from proofflow.services.policy_gate_action_classifier import (
    PolicyGateActionClassification,
    PolicyGateActionSurface,
    classify_policy_gate_action,
)
from proofflow.services.policy_gate_dry_run_context import (
    PolicyGateContextBoundDryRunEvaluation,
    PolicyGateDryRunContext,
    bind_dry_run_context,
)
from proofflow.services.policy_gate_service import PolicyGateEvaluation, PolicyOutcome


_REVIEW_OUTCOMES = {
    PolicyOutcome.WARN,
    PolicyOutcome.REQUIRE_DECISION,
    PolicyOutcome.BLOCK,
    PolicyOutcome.FAIL_CLOSED,
}


@dataclass(frozen=True)
class PolicyGateDryRunObservation:
    classification: PolicyGateActionClassification
    dry_run: PolicyGateContextBoundDryRunEvaluation
    observation_id: str | None = None

    @property
    def would_have_outcome(self) -> PolicyOutcome:
        return self.dry_run.would_have_outcome

    @property
    def non_enforcing(self) -> bool:
        return True

    @property
    def label(self) -> str:
        return "observed_only"

    @property
    def recommended_for_review(self) -> bool:
        return (
            self.classification.high_risk
            or bool(self.classification.missing_invariants)
            or not self.dry_run.context_bound
            or self.dry_run.would_have_outcome in _REVIEW_OUTCOMES
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "would_have_outcome": self.would_have_outcome.value,
            "non_enforcing": self.non_enforcing,
            "label": self.label,
            "recommended_for_review": self.recommended_for_review,
            "classification": self.classification.to_dict(),
            "dry_run": self.dry_run.to_dict(),
        }


def create_policy_gate_dry_run_observation(
    surface: PolicyGateActionSurface,
    evaluation: PolicyGateEvaluation,
    context: PolicyGateDryRunContext,
    observation_id: str | None = None,
) -> PolicyGateDryRunObservation:
    return PolicyGateDryRunObservation(
        classification=classify_policy_gate_action(surface),
        dry_run=bind_dry_run_context(evaluation, context),
        observation_id=observation_id,
    )
