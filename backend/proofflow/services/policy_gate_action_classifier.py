from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import re
from types import MappingProxyType
from typing import Any, TypeVar

from proofflow.services.policy_gate_service import PolicyCategory


T = TypeVar("T")

_NETWORK_COMMAND_PATTERNS = (
    "curl",
    "wget",
    "invoke-webrequest",
    "invoke-restmethod",
    "iwr",
    "irm",
    "http://",
    "https://",
)
_PACKAGE_COMMAND_PATTERNS = (
    "pip install",
    "npm install",
    "pnpm add",
    "yarn add",
    "uv add",
    "poetry add",
)
_PERSISTENCE_COMMAND_PATTERNS = (
    "schtasks",
    "systemctl",
    "start-process",
    "new-service",
    "set-itemproperty",
    "crontab",
)


@dataclass(frozen=True)
class PolicyGateActionSurface:
    action_type: str
    action_category: str | None = None
    affected_paths: tuple[str, ...] = ()
    affected_commands: tuple[str, ...] = ()
    metadata: Mapping[str, Any] | None = None
    has_preview: bool = False
    has_undo: bool = False
    is_destructive: bool = False
    is_restore_related: bool = False
    is_code_workflow: bool = False
    has_test_evidence: bool = False
    has_source_reference: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "affected_paths", tuple(self.affected_paths))
        object.__setattr__(self, "affected_commands", tuple(self.affected_commands))
        object.__setattr__(
            self,
            "metadata",
            _freeze_metadata(self.metadata or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "action_category": self.action_category,
            "affected_paths": list(self.affected_paths),
            "affected_commands": list(self.affected_commands),
            "metadata": _json_safe_value(self.metadata or {}),
            "has_preview": self.has_preview,
            "has_undo": self.has_undo,
            "is_destructive": self.is_destructive,
            "is_restore_related": self.is_restore_related,
            "is_code_workflow": self.is_code_workflow,
            "has_test_evidence": self.has_test_evidence,
            "has_source_reference": self.has_source_reference,
        }


@dataclass(frozen=True)
class PolicyGateActionClassification:
    high_risk: bool
    categories: tuple[PolicyCategory, ...] = ()
    reasons: tuple[str, ...] = ()
    missing_invariants: tuple[str, ...] = ()
    recommended_dry_run: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "categories", tuple(self.categories))
        object.__setattr__(self, "reasons", tuple(self.reasons))
        object.__setattr__(
            self,
            "missing_invariants",
            tuple(self.missing_invariants),
        )

    @property
    def non_authoritative(self) -> bool:
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "high_risk": self.high_risk,
            "categories": [category.value for category in self.categories],
            "reasons": list(self.reasons),
            "missing_invariants": list(self.missing_invariants),
            "recommended_dry_run": self.recommended_dry_run,
            "non_authoritative": self.non_authoritative,
        }


def classify_policy_gate_action(
    surface: PolicyGateActionSurface,
) -> PolicyGateActionClassification:
    categories: list[PolicyCategory] = []
    reasons: list[str] = []

    if surface.is_destructive:
        _append_unique(categories, PolicyCategory.DESTRUCTIVE_LOCAL_OPERATION)
        _append_unique(reasons, "destructive_action")

    if surface.is_restore_related:
        _append_unique(categories, PolicyCategory.BACKUP_RESTORE_TARGET_RISK)
        _append_unique(reasons, "restore_related_action")

    if _matches_any_command(surface.affected_commands, _NETWORK_COMMAND_PATTERNS):
        _append_unique(categories, PolicyCategory.NETWORK_EXECUTION)
        _append_unique(reasons, "network_command_surface")

    if _matches_any_command(surface.affected_commands, _PACKAGE_COMMAND_PATTERNS):
        _append_unique(categories, PolicyCategory.PACKAGE_DEPENDENCY_MUTATION)
        _append_unique(reasons, "package_dependency_command_surface")

    if _matches_any_command(surface.affected_commands, _PERSISTENCE_COMMAND_PATTERNS):
        _append_unique(categories, PolicyCategory.PROCESS_PERSISTENCE)
        _append_unique(reasons, "process_persistence_command_surface")

    high_risk = bool(categories)
    missing_invariants = _missing_invariants(surface, high_risk)

    return PolicyGateActionClassification(
        high_risk=high_risk,
        categories=tuple(categories),
        reasons=tuple(reasons),
        missing_invariants=tuple(missing_invariants),
        recommended_dry_run=high_risk,
    )


def _missing_invariants(
    surface: PolicyGateActionSurface,
    high_risk: bool,
) -> list[str]:
    missing: list[str] = []

    if high_risk and not surface.has_preview:
        missing.append("missing_preview")
    if surface.is_destructive and not surface.has_undo:
        missing.append("missing_undo")
    if _is_artifact_backed(surface) and not surface.has_source_reference:
        missing.append("missing_source_reference")
    if surface.is_code_workflow and not surface.has_test_evidence:
        missing.append("missing_test_evidence")

    return missing


def _is_artifact_backed(surface: PolicyGateActionSurface) -> bool:
    return surface.action_category == "artifact" or bool(
        surface.metadata and surface.metadata.get("artifact_backed") is True
    )


def _matches_any_command(
    commands: tuple[str, ...],
    patterns: tuple[str, ...],
) -> bool:
    return any(
        _matches_command_pattern(command, pattern)
        for command in commands
        for pattern in patterns
    )


def _matches_command_pattern(command: str, pattern: str) -> bool:
    normalized_command = command.lower()
    normalized_pattern = pattern.lower()

    if "://" in normalized_pattern or " " in normalized_pattern:
        return normalized_pattern in normalized_command

    return re.search(
        rf"(?<![a-z0-9_-]){re.escape(normalized_pattern)}(?![a-z0-9_-])",
        normalized_command,
    ) is not None


def _append_unique(values: list[T], value: T) -> None:
    if value not in values:
        values.append(value)


def _freeze_metadata(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(
        {
            str(key): _freeze_metadata_value(metadata_value)
            for key, metadata_value in value.items()
        }
    )


def _freeze_metadata_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_metadata(value)
    if isinstance(value, list | tuple):
        return tuple(_freeze_metadata_value(item) for item in value)
    if isinstance(value, set | frozenset):
        return tuple(_freeze_metadata_value(item) for item in sorted(value, key=repr))
    if isinstance(value, Enum):
        return value.value
    return value


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)
