from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from proofflow.services.policy_gate_service import (
    PolicyGateEvaluation,
    PolicyOutcome,
)


@dataclass(frozen=True)
class PolicyGateDryRunEvaluation:
    evaluation: PolicyGateEvaluation
    missing_context: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "missing_context", tuple(self.missing_context))

    @property
    def would_have_outcome(self) -> PolicyOutcome:
        return self.evaluation.final_outcome or PolicyOutcome.FAIL_CLOSED

    @property
    def non_enforcing(self) -> bool:
        return True

    @property
    def label(self) -> str:
        return "observed_only"

    def to_dict(self) -> dict[str, Any]:
        return {
            "would_have_outcome": self.would_have_outcome.value,
            "non_enforcing": self.non_enforcing,
            "label": self.label,
            "missing_context": list(self.missing_context),
            "evaluation": self.evaluation.to_dict(),
        }
