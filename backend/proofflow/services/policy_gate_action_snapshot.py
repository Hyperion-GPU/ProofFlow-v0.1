from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any

from proofflow.services.policy_gate_action_classifier import PolicyGateActionSurface
from proofflow.services.policy_gate_dry_run_context import PolicyGateDryRunContext


_COMMAND_METADATA_KEYS = ("affected_commands", "commands", "command")
_PATH_METADATA_KEYS = ("affected_paths", "paths", "path")
_PREVIEW_PATH_KEYS = ("from_path", "to_path", "dir_path", "path")
_SOURCE_REFERENCE_KEYS = (
    "source",
    "source_ref",
    "source_reference",
    "artifact_source",
    "artifact_id",
)
_TEST_EVIDENCE_KEYS = (
    "test_evidence",
    "test_result",
    "test_results",
    "test_command",
)
_AUTHORITY_METADATA_KEYS = {
    "allow_execution",
    "block_execution",
    "blocked_execution",
    "final_outcome",
    "would_have_outcome",
    "is_blocking",
    "requires_operator_decision",
}


@dataclass(frozen=True)
class PolicyGateActionSnapshot:
    action_type: str
    case_id: str | None = None
    action_id: str | None = None
    action_category: str | None = None
    status: str | None = None
    preview: Any | None = None
    metadata: Mapping[str, Any] | None = None
    undo: Mapping[str, Any] | None = None
    affected_paths: tuple[str, ...] = ()
    affected_commands: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "affected_paths", tuple(self.affected_paths))
        object.__setattr__(self, "affected_commands", tuple(self.affected_commands))
        object.__setattr__(self, "preview", _freeze_preview_value(self.preview))
        object.__setattr__(self, "metadata", _freeze_mapping(self.metadata or {}))
        object.__setattr__(self, "undo", _freeze_mapping(self.undo or {}))

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "action_id": self.action_id,
            "action_type": self.action_type,
            "action_category": self.action_category,
            "status": self.status,
            "preview_hash": stable_preview_hash(self.preview),
            "metadata": _json_safe_metadata(self.metadata or {}),
            "undo": _json_safe_metadata(self.undo or {}),
            "affected_paths": list(self.affected_paths),
            "affected_commands": list(self.affected_commands),
        }


def stable_preview_hash(preview: Any) -> str | None:
    if _is_missing_preview(preview):
        return None

    canonical_preview = _canonical_preview_value(preview)
    payload = json.dumps(
        canonical_preview,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def action_snapshot_to_surface(
    snapshot: PolicyGateActionSnapshot,
) -> PolicyGateActionSurface:
    preview_hash = stable_preview_hash(snapshot.preview)
    metadata = snapshot.metadata or {}

    return PolicyGateActionSurface(
        action_type=snapshot.action_type,
        action_category=snapshot.action_category,
        affected_paths=_affected_paths_from_snapshot(snapshot),
        affected_commands=_affected_commands_from_snapshot(snapshot),
        metadata=_filtered_metadata(metadata),
        has_preview=preview_hash is not None,
        has_undo=bool(snapshot.undo),
        is_destructive=_is_destructive_snapshot(snapshot),
        is_restore_related=_is_restore_related_snapshot(snapshot),
        is_code_workflow=_is_code_workflow_snapshot(snapshot),
        has_test_evidence=_has_any_present_metadata_value(
            metadata,
            _TEST_EVIDENCE_KEYS,
        ),
        has_source_reference=_has_any_present_metadata_value(
            metadata,
            _SOURCE_REFERENCE_KEYS,
        ),
    )


def action_snapshot_to_context(
    snapshot: PolicyGateActionSnapshot,
    expected_action_id: str | None = None,
    expected_preview_hash: str | None = None,
    policy_evaluation_id: str | None = None,
) -> PolicyGateDryRunContext:
    return PolicyGateDryRunContext(
        case_id=snapshot.case_id,
        action_id=snapshot.action_id,
        preview_hash=stable_preview_hash(snapshot.preview),
        policy_evaluation_id=policy_evaluation_id,
        expected_action_id=expected_action_id,
        expected_preview_hash=expected_preview_hash,
    )


def _is_missing_preview(preview: Any) -> bool:
    if preview is None:
        return True
    if isinstance(preview, str):
        return preview == ""
    if isinstance(preview, Mapping | list | tuple):
        return len(preview) == 0
    return False


def _canonical_preview_value(value: Any) -> Any:
    if value is None or isinstance(value, str | bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise TypeError("preview floats must be finite JSON values")
        return value
    if isinstance(value, tuple | list):
        return [_canonical_preview_value(item) for item in value]
    if isinstance(value, Mapping):
        canonical: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("preview object keys must be strings")
            canonical[key] = _canonical_preview_value(item)
        return canonical

    raise TypeError(
        "preview must contain only JSON primitives, lists, tuples, and mappings"
    )


def _affected_paths_from_snapshot(
    snapshot: PolicyGateActionSnapshot,
) -> tuple[str, ...]:
    paths: list[str] = []
    _append_string_values(paths, snapshot.affected_paths)

    metadata = snapshot.metadata or {}
    for key in _PATH_METADATA_KEYS:
        _append_string_values(paths, metadata.get(key))

    if isinstance(snapshot.preview, Mapping):
        for key in _PREVIEW_PATH_KEYS:
            _append_string_values(paths, snapshot.preview.get(key))

    return tuple(paths)


def _affected_commands_from_snapshot(
    snapshot: PolicyGateActionSnapshot,
) -> tuple[str, ...]:
    commands: list[str] = []
    _append_string_values(commands, snapshot.affected_commands)

    metadata = snapshot.metadata or {}
    for key in _COMMAND_METADATA_KEYS:
        _append_string_values(commands, metadata.get(key))

    return tuple(commands)


def _is_destructive_snapshot(snapshot: PolicyGateActionSnapshot) -> bool:
    metadata = snapshot.metadata or {}
    if _metadata_flag(metadata, "is_destructive", "destructive", "policy_destructive"):
        return True

    return _contains_any(snapshot.action_type, ("delete", "move", "rename", "restore"))


def _is_restore_related_snapshot(snapshot: PolicyGateActionSnapshot) -> bool:
    metadata = snapshot.metadata or {}
    if _metadata_flag(metadata, "is_restore_related", "restore_related"):
        return True

    return _contains_any(snapshot.action_type, ("restore",)) or _contains_any(
        snapshot.action_category,
        ("restore",),
    )


def _is_code_workflow_snapshot(snapshot: PolicyGateActionSnapshot) -> bool:
    metadata = snapshot.metadata or {}
    if _metadata_flag(metadata, "is_code_workflow", "code_workflow"):
        return True

    return snapshot.action_category in {"code", "code_workflow"}


def _metadata_flag(metadata: Mapping[str, Any], *keys: str) -> bool:
    return any(metadata.get(key) is True for key in keys)


def _has_any_present_metadata_value(
    metadata: Mapping[str, Any],
    keys: tuple[str, ...],
) -> bool:
    return any(_is_present(metadata.get(key)) for key in keys if key in metadata)


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value != ""
    if isinstance(value, Mapping | list | tuple | set | frozenset):
        return bool(value)
    return True


def _contains_any(value: str | None, tokens: tuple[str, ...]) -> bool:
    if not value:
        return False
    normalized = value.lower()
    return any(token in normalized for token in tokens)


def _append_string_values(values: list[str], candidate: Any) -> None:
    if isinstance(candidate, str):
        _append_unique_string(values, candidate)
        return

    if isinstance(candidate, list | tuple):
        for item in candidate:
            if isinstance(item, str):
                _append_unique_string(values, item)


def _append_unique_string(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(
        {str(key): _freeze_value(item) for key, item in value.items()}
    )


def _freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _freeze_mapping(value)
    if isinstance(value, list | tuple):
        return tuple(_freeze_value(item) for item in value)
    if isinstance(value, set | frozenset):
        return tuple(_freeze_value(item) for item in sorted(value, key=repr))
    if isinstance(value, Enum):
        return value.value
    return value


def _freeze_preview_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_preview_value(item) for key, item in value.items()}
        )
    if isinstance(value, list | tuple):
        return tuple(_freeze_preview_value(item) for item in value)
    return value


def _filtered_metadata(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(
        {
            str(key): _filtered_metadata_value(item)
            for key, item in value.items()
            if str(key) not in _AUTHORITY_METADATA_KEYS
        }
    )


def _filtered_metadata_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _filtered_metadata(value)
    if isinstance(value, list | tuple):
        return tuple(_filtered_metadata_value(item) for item in value)
    return value


def _json_safe_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): _json_safe_metadata_value(item)
        for key, item in value.items()
        if str(key) not in _AUTHORITY_METADATA_KEYS
    }


def _json_safe_metadata_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _json_safe_metadata(value)
    if isinstance(value, tuple | list):
        return [_json_safe_metadata_value(item) for item in value]
    return _json_safe_value(value)


def _json_safe_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)
