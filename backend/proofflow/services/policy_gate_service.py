from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable


class PolicyOutcome(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    REQUIRE_DECISION = "require_decision"
    BLOCK = "block"
    FAIL_CLOSED = "fail_closed"


class PolicyCategory(str, Enum):
    FILESYSTEM_ESCAPE = "filesystem_escape"
    SECRET_ACCESS = "secret_access"
    NETWORK_EXECUTION = "network_execution"
    PACKAGE_DEPENDENCY_MUTATION = "package_dependency_mutation"
    PROCESS_PERSISTENCE = "process_persistence"
    DESTRUCTIVE_LOCAL_OPERATION = "destructive_local_operation"
    BACKUP_RESTORE_TARGET_RISK = "backup_restore_target_risk"
    EXPLANATION_ACTION_MISMATCH = "explanation_action_mismatch"
    AUTONOMOUS_UNATTENDED_MODE = "autonomous_unattended_mode"


class PolicySeverity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


_OUTCOME_PRECEDENCE: dict[PolicyOutcome, int] = {
    PolicyOutcome.ALLOW: 0,
    PolicyOutcome.WARN: 1,
    PolicyOutcome.REQUIRE_DECISION: 2,
    PolicyOutcome.BLOCK: 3,
    PolicyOutcome.FAIL_CLOSED: 4,
}


@dataclass(frozen=True)
class PolicyGateResult:
    policy_id: str
    policy_name: str
    category: PolicyCategory
    severity: PolicySeverity
    outcome: PolicyOutcome
    reason: str
    matched_surface: str | None = None
    redaction_status: str = "not_applicable"
    affected_paths: tuple[str, ...] = ()
    affected_commands: tuple[str, ...] = ()
    allowed_roots_snapshot: tuple[str, ...] = ()
    related_case_id: str | None = None
    related_action_id: str | None = None
    related_decision_id: str | None = None
    related_evidence_id: str | None = None
    transparency_event_id: str | None = None
    remaining_risks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "affected_paths", tuple(self.affected_paths))
        object.__setattr__(self, "affected_commands", tuple(self.affected_commands))
        object.__setattr__(self, "allowed_roots_snapshot", tuple(self.allowed_roots_snapshot))
        object.__setattr__(self, "remaining_risks", tuple(self.remaining_risks))

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "policy_name": self.policy_name,
            "category": self.category.value,
            "severity": self.severity.value,
            "outcome": self.outcome.value,
            "reason": self.reason,
            "matched_surface": self.matched_surface,
            "redaction_status": self.redaction_status,
            "affected_paths": list(self.affected_paths),
            "affected_commands": list(self.affected_commands),
            "allowed_roots_snapshot": list(self.allowed_roots_snapshot),
            "related_case_id": self.related_case_id,
            "related_action_id": self.related_action_id,
            "related_decision_id": self.related_decision_id,
            "related_evidence_id": self.related_evidence_id,
            "transparency_event_id": self.transparency_event_id,
            "remaining_risks": list(self.remaining_risks),
        }


def is_blocking_outcome(outcome: PolicyOutcome) -> bool:
    return outcome in {PolicyOutcome.BLOCK, PolicyOutcome.FAIL_CLOSED}


def requires_operator_decision(outcome: PolicyOutcome) -> bool:
    return outcome == PolicyOutcome.REQUIRE_DECISION


def outcome_precedence(outcome: PolicyOutcome) -> int:
    return _OUTCOME_PRECEDENCE[outcome]


def most_restrictive_outcome(outcomes: Iterable[PolicyOutcome]) -> PolicyOutcome:
    return max(outcomes, key=outcome_precedence, default=PolicyOutcome.FAIL_CLOSED)
