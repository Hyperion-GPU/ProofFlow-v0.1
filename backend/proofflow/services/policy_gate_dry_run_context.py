from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from proofflow.services.policy_gate_service import (
    PolicyGateEvaluation,
    PolicyOutcome,
)


@dataclass(frozen=True)
class PolicyGateDryRunContext:
    case_id: str | None = None
    action_id: str | None = None
    preview_hash: str | None = None
    policy_evaluation_id: str | None = None
    expected_action_id: str | None = None
    expected_preview_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "action_id": self.action_id,
            "preview_hash": self.preview_hash,
            "policy_evaluation_id": self.policy_evaluation_id,
            "expected_action_id": self.expected_action_id,
            "expected_preview_hash": self.expected_preview_hash,
        }


@dataclass(frozen=True)
class PolicyGateContextBoundDryRunEvaluation:
    evaluation: PolicyGateEvaluation
    context: PolicyGateDryRunContext

    @property
    def missing_context(self) -> tuple[str, ...]:
        missing: list[str] = []
        if not _has_context_value(self.context.case_id):
            missing.append("case_id")
        if not _has_context_value(self.context.action_id):
            missing.append("action_id")
        if not _has_context_value(self.context.preview_hash):
            missing.append("preview_hash")
        return tuple(missing)

    @property
    def context_mismatches(self) -> tuple[str, ...]:
        mismatches: list[str] = []
        if _is_mismatch(self.context.action_id, self.context.expected_action_id):
            mismatches.append("action_id")
        if _is_mismatch(self.context.preview_hash, self.context.expected_preview_hash):
            mismatches.append("preview_hash")
        return tuple(mismatches)

    @property
    def context_bound(self) -> bool:
        return not self.missing_context and not self.context_mismatches

    @property
    def would_have_outcome(self) -> PolicyOutcome:
        if not self.context_bound:
            return PolicyOutcome.FAIL_CLOSED
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
            "context_bound": self.context_bound,
            "missing_context": list(self.missing_context),
            "context_mismatches": list(self.context_mismatches),
            "context": self.context.to_dict(),
            "evaluation": self.evaluation.to_dict(),
        }


def bind_dry_run_context(
    evaluation: PolicyGateEvaluation,
    context: PolicyGateDryRunContext,
) -> PolicyGateContextBoundDryRunEvaluation:
    return PolicyGateContextBoundDryRunEvaluation(
        evaluation=evaluation,
        context=context,
    )


def _has_context_value(value: str | None) -> bool:
    return value is not None and value != ""


def _is_mismatch(actual: str | None, expected: str | None) -> bool:
    return _has_context_value(actual) and _has_context_value(expected) and actual != expected
