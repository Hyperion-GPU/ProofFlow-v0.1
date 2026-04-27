from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from proofflow.config import get_data_dir, get_db_path

FILESYSTEM_ACTION_KINDS = {"move_file", "rename_file", "mkdir_dir"}
LOCALPROOF_SCOPE_KIND = "localproof_file_cleanup"
LOCALPROOF_METADATA_SOURCE = "localproof_suggest_actions"


class ActionSafetyError(ValueError):
    """Raised when an action attempts to leave its declared file scope."""


@dataclass(frozen=True)
class ProtectedPath:
    path: Path
    label: str
    is_directory: bool


def build_localproof_scope_metadata(source_root: Path, target_root: Path) -> dict[str, Any]:
    resolved_source_root = resolve_scope_root(str(source_root), "source_root")
    resolved_target_root = resolve_scope_root(str(target_root), "target_root")
    _ensure_path_not_protected(resolved_source_root, "source_root")
    _ensure_path_not_protected(resolved_target_root, "target_root")

    return {
        "source": LOCALPROOF_METADATA_SOURCE,
        "scope_kind": LOCALPROOF_SCOPE_KIND,
        "source_root": str(resolved_source_root),
        "target_root": str(resolved_target_root),
        "allowed_roots": [
            str(resolved_source_root),
            str(resolved_target_root),
        ],
    }


def validate_filesystem_action_scope(
    kind: str,
    preview: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    if kind not in FILESYSTEM_ACTION_KINDS:
        return dict(metadata)

    normalized_metadata, allowed_roots = _normalize_scope_metadata(metadata)
    action_paths = _paths_for_action(kind, preview)
    for label, path in action_paths:
        _ensure_inside_allowed_roots(path, allowed_roots, label)
        _ensure_path_not_protected(path, label)
    return normalized_metadata


def resolve_scope_root(value: str, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ActionSafetyError(f"{label} must be a non-empty absolute path")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ActionSafetyError(f"{label} must be an absolute path")
    return path.resolve(strict=False)


def is_path_at_or_under(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _normalize_scope_metadata(
    metadata: dict[str, Any],
) -> tuple[dict[str, Any], list[Path]]:
    normalized = dict(metadata)
    raw_allowed_roots = metadata.get("allowed_roots")
    if not isinstance(raw_allowed_roots, list) or not raw_allowed_roots:
        raise ActionSafetyError("filesystem actions require metadata.allowed_roots")

    allowed_roots: list[Path] = []
    for index, raw_root in enumerate(raw_allowed_roots):
        if not isinstance(raw_root, str) or not raw_root:
            raise ActionSafetyError("metadata.allowed_roots must contain non-empty paths")
        allowed_roots.append(resolve_scope_root(raw_root, f"allowed_roots[{index}]"))

    normalized["allowed_roots"] = [str(root) for root in allowed_roots]

    source_root = _normalize_optional_root(metadata, "source_root")
    target_root = _normalize_optional_root(metadata, "target_root")
    if source_root is not None:
        normalized["source_root"] = str(source_root)
    if target_root is not None:
        normalized["target_root"] = str(target_root)

    if metadata.get("source") == LOCALPROOF_METADATA_SOURCE:
        _validate_localproof_scope(normalized, allowed_roots, source_root, target_root)

    return normalized, allowed_roots


def _normalize_optional_root(metadata: dict[str, Any], key: str) -> Path | None:
    if key not in metadata:
        return None
    raw_value = metadata.get(key)
    if not isinstance(raw_value, str) or not raw_value:
        raise ActionSafetyError(f"metadata.{key} must be a non-empty absolute path")
    return resolve_scope_root(raw_value, key)


def _validate_localproof_scope(
    metadata: dict[str, Any],
    allowed_roots: list[Path],
    source_root: Path | None,
    target_root: Path | None,
) -> None:
    if metadata.get("scope_kind") != LOCALPROOF_SCOPE_KIND:
        raise ActionSafetyError("LocalProof actions require localproof_file_cleanup scope")
    if source_root is None or target_root is None:
        raise ActionSafetyError("LocalProof actions require source_root and target_root")
    if not any(root == source_root for root in allowed_roots):
        raise ActionSafetyError("LocalProof source_root must be listed in allowed_roots")
    if not any(root == target_root for root in allowed_roots):
        raise ActionSafetyError("LocalProof target_root must be listed in allowed_roots")


def _paths_for_action(kind: str, preview: dict[str, Any]) -> list[tuple[str, Path]]:
    if kind in {"move_file", "rename_file"}:
        return [
            ("from_path", _resolve_action_path(preview.get("from_path"), "from_path")),
            ("to_path", _resolve_action_path(preview.get("to_path"), "to_path")),
        ]
    if kind == "mkdir_dir":
        return [("dir_path", _resolve_action_path(preview.get("dir_path"), "dir_path"))]
    raise ActionSafetyError(f"unsupported filesystem action kind: {kind}")


def _resolve_action_path(value: Any, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ActionSafetyError(f"{label} must be a non-empty absolute path")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ActionSafetyError(f"{label} must be an absolute path")
    return path.resolve(strict=False)


def _ensure_inside_allowed_roots(path: Path, allowed_roots: list[Path], label: str) -> None:
    if any(is_path_at_or_under(path, root) for root in allowed_roots):
        return
    roots = ", ".join(str(root) for root in allowed_roots)
    raise ActionSafetyError(f"{label} is outside action allowed_roots: {path}; allowed: {roots}")


def _ensure_path_not_protected(path: Path, label: str) -> None:
    resolved_path = path.resolve(strict=False)
    for protected in _protected_paths():
        if protected.is_directory and is_path_at_or_under(resolved_path, protected.path):
            raise ActionSafetyError(f"{label} cannot touch {protected.label}: {resolved_path}")
        if not protected.is_directory and resolved_path == protected.path:
            raise ActionSafetyError(f"{label} cannot touch {protected.label}: {resolved_path}")


def _protected_paths() -> list[ProtectedPath]:
    data_dir = get_data_dir()
    return [
        ProtectedPath(get_db_path(), "ProofFlow database", False),
        ProtectedPath(data_dir / "proof_packets", "ProofFlow proof_packets directory", True),
        ProtectedPath(data_dir, "ProofFlow data directory", True),
    ]
