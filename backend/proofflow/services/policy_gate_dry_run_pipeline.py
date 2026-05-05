from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from proofflow.services.policy_gate_action_snapshot import (
    PolicyGateActionSnapshot,
    action_snapshot_to_context,
    action_snapshot_to_surface,
)
from proofflow.services.policy_gate_dry_run_observation import (
    PolicyGateDryRunObservation,
    create_policy_gate_dry_run_observation,
)
from proofflow.services.policy_gate_service import (
    PolicyGateEvaluation,
    PolicyOutcome,
)


@dataclass(frozen=True)
class PolicyGateDryRunPipelineResult:
    snapshot: PolicyGateActionSnapshot
    observation: PolicyGateDryRunObservation
    pipeline_id: str | None = None

    @property
    def would_have_outcome(self) -> PolicyOutcome:
        return self.observation.would_have_outcome

    @property
    def non_enforcing(self) -> bool:
        return True

    @property
    def label(self) -> str:
        return "observed_only"

    @property
    def recommended_for_review(self) -> bool:
        return self.observation.recommended_for_review

    @property
    def high_risk(self) -> bool:
        return self.observation.classification.high_risk

    @property
    def context_bound(self) -> bool:
        return self.observation.dry_run.context_bound

    def to_dict(self) -> dict[str, Any]:
        return {
            "pipeline_id": self.pipeline_id,
            "would_have_outcome": self.would_have_outcome.value,
            "non_enforcing": self.non_enforcing,
            "label": self.label,
            "recommended_for_review": self.recommended_for_review,
            "high_risk": self.high_risk,
            "context_bound": self.context_bound,
            "snapshot": self.snapshot.to_dict(),
            "observation": self.observation.to_dict(),
        }


def evaluate_dry_run_pipeline(
    snapshot: PolicyGateActionSnapshot,
    evaluation: PolicyGateEvaluation,
    *,
    expected_action_id: str | None = None,
    expected_preview_hash: str | None = None,
    policy_evaluation_id: str | None = None,
    pipeline_id: str | None = None,
    observation_id: str | None = None,
) -> PolicyGateDryRunPipelineResult:
    """Orchestrate the full dry-run observation pipeline.

    Composes: snapshot -> surface -> classify + context -> observation.

    This is a pure, stateless function. It does not write to the database,
    call external services, or enforce any runtime behavior. The result is
    a non-enforcing observation record.
    """
    surface = action_snapshot_to_surface(snapshot)
    context = action_snapshot_to_context(
        snapshot,
        expected_action_id=expected_action_id,
        expected_preview_hash=expected_preview_hash,
        policy_evaluation_id=policy_evaluation_id,
    )
    observation = create_policy_gate_dry_run_observation(
        surface=surface,
        evaluation=evaluation,
        context=context,
        observation_id=observation_id,
    )
    return PolicyGateDryRunPipelineResult(
        snapshot=snapshot,
        observation=observation,
        pipeline_id=pipeline_id,
    )
