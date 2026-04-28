from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any

from proofflow.config import get_data_dir, get_db_path
from proofflow.db import connect, new_uuid, utc_now_iso
from proofflow.models.schemas import (
    RestorePlannedWrite,
    RestorePreviewRequest,
    RestorePreviewResponse,
    RestoreRisk,
    RestoreTarget,
    RestoreToNewLocationRequest,
    RestoreToNewLocationResponse,
)
from proofflow.services.backup_service import (
    PROOF_PACKETS_DIRNAME,
    SCHEMA_VERSION,
    BackupError,
    BackupIntegrityResult,
    verify_backup_integrity_read_only,
)
from proofflow.services.errors import NotFoundError
from proofflow.services.json_utils import dumps_metadata
from proofflow.version import __version__


class RestoreError(ValueError):
    """Raised when a restore request violates the foundation safety contract."""


@dataclass(frozen=True)
class RestorePlan:
    backup_id: str
    case_id: str | None
    target_db_path: Path
    target_data_dir: Path
    planned_writes: list[RestorePlannedWrite]
    plan_hash: str
    schema_risks: list[RestoreRisk]
    version_risks: list[RestoreRisk]
    warnings: list[str]
    manifest_sha256: str
    archive_sha256: str


@dataclass(frozen=True)
class RestorePreviewRecord:
    id: str
    backup_id: str
    case_id: str | None
    target_db_path: str
    target_data_dir: str
    plan_hash: str
    archive_sha256: str | None
    manifest_sha256: str | None
    planned_writes: list[dict[str, Any]]
    schema_risks: list[dict[str, Any]]
    version_risks: list[dict[str, Any]]
    warnings: list[str]
    created_at: str
    updated_at: str


def preview_restore(payload: RestorePreviewRequest) -> RestorePreviewResponse:
    plan = _build_restore_plan(
        payload.backup_id,
        payload.target_db_path,
        payload.target_data_dir,
    )
    restore_preview_id = _record_restore_preview(plan)
    return _preview_response(restore_preview_id, plan)


def restore_to_new_location(payload: RestoreToNewLocationRequest) -> RestoreToNewLocationResponse:
    preview = _get_restore_preview(payload.accepted_preview_id)
    target_db_path = _resolve_local_path(payload.target_db_path, "target_db_path")
    target_data_dir = _resolve_local_path(payload.target_data_dir, "target_data_dir")

    if preview.backup_id != payload.backup_id:
        raise RestoreError("accepted preview belongs to a different backup_id")
    if preview.target_db_path != str(target_db_path):
        raise RestoreError("accepted preview target_db_path does not match request")
    if preview.target_data_dir != str(target_data_dir):
        raise RestoreError("accepted preview target_data_dir does not match request")

    plan = _build_restore_plan(payload.backup_id, str(target_db_path), str(target_data_dir))
    if plan.plan_hash != preview.plan_hash:
        raise RestoreError("restore preview is stale; create a new preview")
    overwrites = [write for write in plan.planned_writes if write.would_overwrite]
    if overwrites:
        raise RestoreError("restore would overwrite existing target files; create a new preview after clearing targets")

    restored_files = _restore_plan_files(plan)
    warnings = list(plan.warnings)
    try:
        _record_restore_result(plan, payload.accepted_preview_id, restored_files)
    except Exception as error:
        warnings.append(f"restore result evidence could not be recorded: {error}")
    return RestoreToNewLocationResponse(
        backup_id=plan.backup_id,
        restore_preview_id=payload.accepted_preview_id,
        case_id=plan.case_id,
        target=RestoreTarget(
            db_path=str(plan.target_db_path),
            data_dir=str(plan.target_data_dir),
        ),
        restored_files=restored_files,
        status="restored_to_new_location",
        warnings=warnings,
    )


def _build_restore_plan(
    backup_id: str,
    target_db_path: str,
    target_data_dir: str,
) -> RestorePlan:
    integrity = _load_verified_backup(backup_id)
    resolved_target_db_path = _resolve_local_path(target_db_path, "target_db_path")
    resolved_target_data_dir = _resolve_local_path(target_data_dir, "target_data_dir")
    _validate_restore_targets(resolved_target_db_path, resolved_target_data_dir)

    schema_risks, version_risks = _manifest_version_risks(integrity.manifest)
    warnings = _manifest_warnings(integrity.manifest)
    planned_writes = _planned_writes_from_manifest(
        integrity.manifest,
        target_db_path=resolved_target_db_path,
        target_data_dir=resolved_target_data_dir,
    )
    plan_hash = _compute_plan_hash(
        backup_id=backup_id,
        manifest_sha256=integrity.manifest_sha256,
        archive_sha256=integrity.archive_sha256,
        target_db_path=resolved_target_db_path,
        target_data_dir=resolved_target_data_dir,
        planned_writes=planned_writes,
        schema_risks=schema_risks,
        version_risks=version_risks,
        warnings=warnings,
    )
    return RestorePlan(
        backup_id=backup_id,
        case_id=integrity.record.case_id,
        target_db_path=resolved_target_db_path,
        target_data_dir=resolved_target_data_dir,
        planned_writes=planned_writes,
        plan_hash=plan_hash,
        schema_risks=schema_risks,
        version_risks=version_risks,
        warnings=warnings,
        manifest_sha256=integrity.manifest_sha256,
        archive_sha256=integrity.archive_sha256,
    )


def _load_verified_backup(backup_id: str) -> BackupIntegrityResult:
    try:
        return verify_backup_integrity_read_only(backup_id)
    except BackupError as error:
        raise RestoreError(str(error)) from error


def _planned_writes_from_manifest(
    manifest: dict[str, Any],
    *,
    target_db_path: Path,
    target_data_dir: Path,
) -> list[RestorePlannedWrite]:
    files = manifest.get("files")
    if not isinstance(files, list):
        raise RestoreError("manifest files field is missing or invalid")

    planned_writes: list[RestorePlannedWrite] = []
    for entry in files:
        if not isinstance(entry, dict):
            raise RestoreError("manifest file entry must be a JSON object")
        archive_relative_path = _safe_archive_relative_path(entry.get("relative_path"))
        role = _required_string(entry, "role")
        sha256 = _required_string(entry, "sha256")
        size_bytes = _required_non_negative_int(entry, "size_bytes")
        target_path = _target_for_archive_member(
            archive_relative_path,
            target_db_path=target_db_path,
            target_data_dir=target_data_dir,
        )
        _assert_safe_existing_parent_chain(target_path)
        would_overwrite = target_path.exists() or target_path.is_symlink()
        planned_writes.append(
            RestorePlannedWrite(
                archive_relative_path=archive_relative_path,
                target_path=str(target_path),
                role=role,
                action="overwrite" if would_overwrite else "create",
                size_bytes=size_bytes,
                sha256=sha256,
                would_overwrite=would_overwrite,
            )
        )
    return sorted(planned_writes, key=lambda item: item.archive_relative_path)


def _target_for_archive_member(
    archive_relative_path: str,
    *,
    target_db_path: Path,
    target_data_dir: Path,
) -> Path:
    if archive_relative_path == "db/proofflow.db":
        return target_db_path
    if archive_relative_path.startswith("data/"):
        target = (target_data_dir / archive_relative_path.removeprefix("data/")).resolve(strict=False)
        _assert_under(target, target_data_dir, "data restore target escaped target_data_dir")
        return target
    if archive_relative_path.startswith(f"{PROOF_PACKETS_DIRNAME}/"):
        relative = archive_relative_path.removeprefix(f"{PROOF_PACKETS_DIRNAME}/")
        target = (target_data_dir / PROOF_PACKETS_DIRNAME / relative).resolve(strict=False)
        _assert_under(target, target_data_dir, "proof packet restore target escaped target_data_dir")
        return target
    raise RestoreError(f"unsupported archive member for restore: {archive_relative_path}")


def _safe_archive_relative_path(value: Any) -> str:
    if not isinstance(value, str) or not value:
        raise RestoreError("archive relative path is missing")
    if "\\" in value:
        raise RestoreError(f"unsafe archive member contains backslash: {value}")
    if value.startswith("/") or PureWindowsPath(value).drive:
        raise RestoreError(f"unsafe archive member is absolute: {value}")
    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise RestoreError(f"unsafe archive member contains traversal: {value}")
    return value


def _manifest_version_risks(manifest: dict[str, Any]) -> tuple[list[RestoreRisk], list[RestoreRisk]]:
    app_version = manifest.get("app_version")
    schema_version = manifest.get("schema_version")
    if not isinstance(app_version, str) or not app_version:
        raise RestoreError("manifest app_version is required for restore trust")
    if not isinstance(schema_version, str) or not schema_version:
        raise RestoreError("manifest schema_version is required for restore trust")

    schema_risks: list[RestoreRisk] = []
    version_risks: list[RestoreRisk] = []
    if app_version != __version__:
        version_risks.append(
            RestoreRisk(
                code="app_version_mismatch",
                message=f"Backup app_version {app_version} differs from runtime {__version__}.",
            )
        )
    if schema_version != SCHEMA_VERSION:
        schema_risks.append(
            RestoreRisk(
                code="schema_version_mismatch",
                message=f"Backup schema_version {schema_version} differs from runtime {SCHEMA_VERSION}.",
            )
        )
    return schema_risks, version_risks


def _manifest_warnings(manifest: dict[str, Any]) -> list[str]:
    warnings = manifest.get("warnings")
    if not isinstance(warnings, list):
        return []
    return [str(warning) for warning in warnings]


def _record_restore_preview(plan: RestorePlan) -> str:
    preview_id = new_uuid()
    created_at = utc_now_iso()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO restore_previews (
                id, backup_id, case_id, target_db_path, target_data_dir,
                plan_hash, archive_sha256, manifest_sha256, planned_writes_json,
                schema_risks_json, version_risks_json, warnings_json,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                preview_id,
                plan.backup_id,
                plan.case_id,
                str(plan.target_db_path),
                str(plan.target_data_dir),
                plan.plan_hash,
                plan.archive_sha256,
                plan.manifest_sha256,
                _json_list([write.model_dump() for write in plan.planned_writes]),
                _json_list([risk.model_dump() for risk in plan.schema_risks]),
                _json_list([risk.model_dump() for risk in plan.version_risks]),
                _json_list(plan.warnings),
                created_at,
                created_at,
            ),
        )
        if plan.case_id is not None:
            connection.execute(
                """
                INSERT INTO evidence (
                    id, case_id, artifact_id, claim_id, evidence_type, content,
                    source_ref, metadata_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_uuid(),
                    plan.case_id,
                    None,
                    None,
                    "restore_preview",
                    "Restore-to-new-location preview was created for risk review.",
                    preview_id,
                    dumps_metadata(
                        {
                            "workflow": "managed_restore",
                            "backup_id": plan.backup_id,
                            "restore_preview_id": preview_id,
                            "plan_hash": plan.plan_hash,
                        }
                    ),
                    created_at,
                    created_at,
                ),
            )
        connection.commit()
    return preview_id


def _record_restore_result(plan: RestorePlan, preview_id: str, restored_files: int) -> None:
    if plan.case_id is None:
        return
    now = utc_now_iso()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO evidence (
                id, case_id, artifact_id, claim_id, evidence_type, content,
                source_ref, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_uuid(),
                plan.case_id,
                None,
                None,
                "restore_to_new_location",
                f"Restored backup to a new inspection location with {restored_files} files.",
                preview_id,
                dumps_metadata(
                    {
                        "workflow": "managed_restore",
                        "backup_id": plan.backup_id,
                        "restore_preview_id": preview_id,
                        "target_db_path": str(plan.target_db_path),
                        "target_data_dir": str(plan.target_data_dir),
                        "restored_files": restored_files,
                    }
                ),
                now,
                now,
            ),
        )
        connection.commit()


def _restore_plan_files(plan: RestorePlan) -> int:
    created_files: list[Path] = []
    created_dirs: list[Path] = []
    try:
        with zipfile.ZipFile(_archive_path_for_backup(plan.backup_id), "r") as archive:
            for planned_write in plan.planned_writes:
                target_path = Path(planned_write.target_path)
                if planned_write.would_overwrite or target_path.exists() or target_path.is_symlink():
                    raise RestoreError(f"restore would overwrite existing target: {target_path}")
                _assert_restore_write_target(target_path, plan)
                content = archive.read(planned_write.archive_relative_path)
                _write_restore_file(target_path, content, created_files, created_dirs)
    except RestoreError:
        _cleanup_partial_restore(created_files, created_dirs)
        raise
    except (OSError, KeyError, zipfile.BadZipFile) as error:
        _cleanup_partial_restore(created_files, created_dirs)
        raise RestoreError(f"restore write failed: {error}") from error
    return len(created_files)


def _write_restore_file(
    target_path: Path,
    content: bytes,
    created_files: list[Path],
    created_dirs: list[Path],
) -> None:
    _assert_safe_existing_parent_chain(target_path)
    _create_missing_parent_dirs(target_path.parent, created_dirs)
    if target_path.exists() or target_path.is_symlink():
        raise RestoreError(f"restore would overwrite existing target: {target_path}")
    target_path.write_bytes(content)
    created_files.append(target_path)


def _create_missing_parent_dirs(parent: Path, created_dirs: list[Path]) -> None:
    if parent.exists() and not parent.is_dir():
        raise RestoreError(f"restore target parent is not a directory: {parent}")
    missing: list[Path] = []
    current = parent
    while not current.exists():
        missing.append(current)
        current = current.parent
    if current.is_symlink():
        raise RestoreError(f"restore target parent contains a symlink: {current}")
    if not current.is_dir():
        raise RestoreError(f"restore target parent is not a directory: {current}")
    for directory in reversed(missing):
        directory.mkdir()
        created_dirs.append(directory)


def _cleanup_partial_restore(created_files: list[Path], created_dirs: list[Path]) -> None:
    for path in reversed(created_files):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    for path in sorted(created_dirs, key=lambda item: len(item.parts), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass


def _archive_path_for_backup(backup_id: str) -> Path:
    integrity = _load_verified_backup(backup_id)
    return Path(integrity.record.archive_path)


def _get_restore_preview(preview_id: str) -> RestorePreviewRecord:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM restore_previews WHERE id = ?",
            (preview_id,),
        ).fetchone()
    if row is None:
        raise NotFoundError(f"restore preview not found: {preview_id}")
    return RestorePreviewRecord(
        id=row["id"],
        backup_id=row["backup_id"],
        case_id=row["case_id"],
        target_db_path=row["target_db_path"],
        target_data_dir=row["target_data_dir"],
        plan_hash=row["plan_hash"],
        archive_sha256=row["archive_sha256"],
        manifest_sha256=row["manifest_sha256"],
        planned_writes=_loads_json_list(row["planned_writes_json"]),
        schema_risks=_loads_json_list(row["schema_risks_json"]),
        version_risks=_loads_json_list(row["version_risks_json"]),
        warnings=[str(item) for item in _loads_json_list(row["warnings_json"])],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _preview_response(preview_id: str, plan: RestorePlan) -> RestorePreviewResponse:
    return RestorePreviewResponse(
        restore_preview_id=preview_id,
        backup_id=plan.backup_id,
        case_id=plan.case_id,
        verified=True,
        target=RestoreTarget(
            db_path=str(plan.target_db_path),
            data_dir=str(plan.target_data_dir),
        ),
        planned_writes=plan.planned_writes,
        plan_hash=plan.plan_hash,
        schema_risks=plan.schema_risks,
        version_risks=plan.version_risks,
        warnings=plan.warnings,
    )


def _validate_restore_targets(target_db_path: Path, target_data_dir: Path) -> None:
    live_db_path = get_db_path().resolve(strict=False)
    live_data_dir = get_data_dir().resolve(strict=False)
    live_proof_packets_dir = (live_data_dir / PROOF_PACKETS_DIRNAME).resolve(strict=False)

    if target_db_path == live_db_path:
        raise RestoreError("target_db_path must not be the current live PROOFFLOW_DB_PATH")
    if _path_overlaps(target_db_path, live_data_dir) or _path_overlaps(target_db_path, live_proof_packets_dir):
        raise RestoreError("target_db_path must not overlap live ProofFlow managed data roots")
    if target_data_dir == live_data_dir:
        raise RestoreError("target_data_dir must not be the current live PROOFFLOW_DATA_DIR")
    if _path_overlaps(target_data_dir, live_data_dir) or _path_overlaps(target_data_dir, live_proof_packets_dir):
        raise RestoreError("target_data_dir must not overlap live ProofFlow managed data roots")
    if _path_overlaps(target_data_dir, live_db_path):
        raise RestoreError("target_data_dir must not overlap the current live PROOFFLOW_DB_PATH")
    if _path_overlaps(target_db_path, target_data_dir):
        raise RestoreError("target_db_path must not be inside target_data_dir")


def _assert_restore_write_target(target_path: Path, plan: RestorePlan) -> None:
    if target_path == plan.target_db_path:
        return
    _assert_under(target_path, plan.target_data_dir, "restore write escaped target_data_dir")


def _assert_safe_existing_parent_chain(target_path: Path) -> None:
    current = target_path.parent
    while True:
        if current.is_symlink():
            raise RestoreError(f"restore target parent contains a symlink: {current}")
        if current.exists():
            if not current.is_dir():
                raise RestoreError(f"restore target parent is not a directory: {current}")
            return
        if current.parent == current:
            return
        current = current.parent


def _assert_under(path: Path, root: Path, message: str) -> None:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError as error:
        raise RestoreError(message) from error


def _path_overlaps(left: Path, right: Path) -> bool:
    return _is_at_or_under(left, right) or _is_at_or_under(right, left)


def _is_at_or_under(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def _resolve_local_path(raw_path: str, label: str) -> Path:
    path = Path(raw_path).expanduser()
    if not str(path).strip():
        raise RestoreError(f"{label} is required")
    _reject_linked_parent_chain(path, label)
    return path.resolve(strict=False)


def _reject_linked_parent_chain(path: Path, label: str) -> None:
    current = path.parent
    while True:
        if _is_link_like(current):
            raise RestoreError(f"{label} parent contains a symlink or junction: {current}")
        if current.exists():
            if not current.is_dir():
                raise RestoreError(f"{label} parent is not a directory: {current}")
        if current.parent == current:
            return
        current = current.parent


def _is_link_like(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    return bool(is_junction and is_junction())


def _compute_plan_hash(
    *,
    backup_id: str,
    manifest_sha256: str,
    archive_sha256: str,
    target_db_path: Path,
    target_data_dir: Path,
    planned_writes: list[RestorePlannedWrite],
    schema_risks: list[RestoreRisk],
    version_risks: list[RestoreRisk],
    warnings: list[str],
) -> str:
    payload = {
        "backup_id": backup_id,
        "manifest_sha256": manifest_sha256,
        "archive_sha256": archive_sha256,
        "target_db_path": str(target_db_path),
        "target_data_dir": str(target_data_dir),
        "planned_writes": [write.model_dump() for write in planned_writes],
        "schema_risks": [risk.model_dump() for risk in schema_risks],
        "version_risks": [risk.model_dump() for risk in version_risks],
        "warnings": warnings,
    }
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _required_string(entry: dict[str, Any], field_name: str) -> str:
    value = entry.get(field_name)
    if not isinstance(value, str) or not value:
        raise RestoreError(f"manifest file entry {field_name} is required")
    return value


def _required_non_negative_int(entry: dict[str, Any], field_name: str) -> int:
    value = entry.get(field_name)
    if not isinstance(value, int) or value < 0:
        raise RestoreError(f"manifest file entry {field_name} must be a non-negative integer")
    return value


def _json_list(items: list[Any]) -> str:
    return json.dumps(items, ensure_ascii=False, sort_keys=True)


def _loads_json_list(raw_json: str | None) -> list[Any]:
    if not raw_json:
        return []
    value = json.loads(raw_json)
    if not isinstance(value, list):
        raise RestoreError("restore preview JSON field must be a list")
    return value
