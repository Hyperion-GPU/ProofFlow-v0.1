from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from proofflow.config import get_data_dir, get_db_path
from proofflow.db import connect, new_uuid, utc_now_iso
from proofflow.models.schemas import (
    BackupCreateRequest,
    BackupCreateResponse,
    BackupDetailResponse,
    BackupHashMismatch,
    BackupListItem,
    BackupListResponse,
    BackupManifestSummary,
    BackupPreviewRequest,
    BackupPreviewResponse,
    BackupSource,
    BackupVerificationSummary,
    BackupVerifyRequest,
    BackupVerifyResponse,
    PlannedBackupFile,
)
from proofflow.services.errors import NotFoundError
from proofflow.services.json_utils import dumps_metadata
from proofflow.version import __version__

APP_NAME = "ProofFlow"
MANIFEST_VERSION = "1"
SCHEMA_VERSION = "v0.1"
ARCHIVE_FORMAT = "zip"
PROOF_PACKETS_DIRNAME = "proof_packets"
SQLITE_SNAPSHOT_RELATIVE_PATH = "db/proofflow.db"


class BackupError(ValueError):
    """Raised when a managed backup request violates the safety contract."""


@dataclass(frozen=True)
class PlannedFile:
    role: str
    relative_path: str
    source_path: Path
    size_bytes: int


@dataclass(frozen=True)
class BackupPlan:
    source: BackupSource
    backup_root: Path
    planned_files: list[PlannedFile]
    warnings: list[str]


@dataclass(frozen=True)
class BackupRecord:
    id: str
    case_id: str | None
    label: str | None
    status: str
    archive_path: str
    manifest_path: str
    manifest_sha256: str | None
    archive_sha256: str | None
    archive_size_bytes: int | None
    file_count: int | None
    verified_at: str | None
    warnings: list[str]
    created_at: str
    updated_at: str


def preview_backup(payload: BackupPreviewRequest) -> BackupPreviewResponse:
    plan = _build_backup_plan(
        payload.backup_root,
        include_data_dir=payload.include_data_dir,
        include_proof_packets=payload.include_proof_packets,
        require_database=False,
    )
    return BackupPreviewResponse(
        source=plan.source,
        planned_files=[
            PlannedBackupFile(
                role=file.role,
                relative_path=file.relative_path,
                size_bytes=file.size_bytes,
                source_path=str(file.source_path),
            )
            for file in plan.planned_files
        ],
        warnings=plan.warnings,
        would_create_case=True,
    )


def create_backup(payload: BackupCreateRequest) -> BackupCreateResponse:
    plan = _build_backup_plan(
        payload.backup_root,
        include_data_dir=True,
        include_proof_packets=True,
        require_database=True,
    )
    backup_root = plan.backup_root
    backup_id = _new_backup_id()
    staging_dir = backup_root / f".proofflow-backup-staging-{backup_id}"
    archive_path = backup_root / f"{backup_id}.zip"
    manifest_path = backup_root / f"{backup_id}.manifest.json"
    warnings = list(plan.warnings)
    committed = False

    if archive_path.exists() or manifest_path.exists() or staging_dir.exists():
        raise BackupError(f"backup output already exists for generated id: {backup_id}")

    staged_files: list[dict[str, Any]] = []

    try:
        _prepare_backup_root(backup_root)
        staging_dir.mkdir(parents=False, exist_ok=False)
        source_db_path = Path(plan.source.db_path)
        for planned_file in plan.planned_files:
            destination = staging_dir / planned_file.relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            if planned_file.role == "sqlite_db":
                _snapshot_sqlite_database(source_db_path, destination)
            else:
                if _is_symlink(planned_file.source_path):
                    warnings.append(f"Skipped symlink during copy: {planned_file.source_path}")
                    continue
                shutil.copy2(planned_file.source_path, destination, follow_symlinks=False)

            staged_files.append(_manifest_file_entry(planned_file.role, planned_file.relative_path, destination))

        if not staged_files:
            raise BackupError("backup has no files to archive")

        _write_archive(archive_path, staging_dir, staged_files)
        archive_sha256 = _sha256_file(archive_path)
        archive_size_bytes = archive_path.stat().st_size
        created_at = utc_now_iso()
        manifest = {
            "manifest_version": MANIFEST_VERSION,
            "app_name": APP_NAME,
            "app_version": __version__,
            "schema_version": SCHEMA_VERSION,
            "created_at": created_at,
            "backup_id": backup_id,
            "source": {
                "db_path": plan.source.db_path,
                "data_dir": plan.source.data_dir,
                "proof_packets_dir": plan.source.proof_packets_dir,
            },
            "files": staged_files,
            "archive": {
                "format": ARCHIVE_FORMAT,
                "sha256": archive_sha256,
                "size_bytes": archive_size_bytes,
            },
            "warnings": warnings,
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest_sha256 = _sha256_file(manifest_path)
        case_id = _record_created_backup(
            backup_id=backup_id,
            label=payload.label,
            archive_path=archive_path,
            manifest_path=manifest_path,
            manifest_sha256=manifest_sha256,
            archive_sha256=archive_sha256,
            archive_size_bytes=archive_size_bytes,
            file_count=len(staged_files),
            warnings=warnings,
            created_at=created_at,
        )
        response = BackupCreateResponse(
            backup_id=backup_id,
            case_id=case_id,
            archive_path=str(archive_path),
            manifest_path=str(manifest_path),
            manifest_sha256=manifest_sha256,
            archive_sha256=archive_sha256,
            warnings=warnings,
        )
        committed = True
        return response
    except OSError as error:
        raise BackupError(f"backup create failed: {error}") from error
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        if not committed:
            _remove_generated_outputs(archive_path, manifest_path)


def list_backups() -> BackupListResponse:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM backups
            ORDER BY created_at DESC, id DESC
            """
        ).fetchall()
    return BackupListResponse(
        backups=[
            BackupListItem(
                backup_id=row["id"],
                created_at=row["created_at"],
                status=row["status"],
                verified_at=row["verified_at"],
                archive_path=row["archive_path"],
            )
            for row in rows
        ]
    )


def get_backup(backup_id: str) -> BackupDetailResponse:
    record = _get_backup_record(backup_id)
    manifest_summary: BackupManifestSummary | None = None
    warnings = list(record.warnings)
    errors: list[str] = []
    manifest_path = Path(record.manifest_path)

    if not manifest_path.exists():
        message = f"manifest file is missing: {manifest_path}"
        warnings.append(message)
        errors.append(message)
    else:
        try:
            manifest = _read_manifest(manifest_path)
            manifest_summary = BackupManifestSummary(
                manifest_version=_string_or_none(manifest.get("manifest_version")),
                app_version=_string_or_none(manifest.get("app_version")),
                schema_version=_string_or_none(manifest.get("schema_version")),
            )
        except BackupError as error:
            message = str(error)
            warnings.append(message)
            errors.append(message)

    verification_status = record.status if record.status == "verified" else "not_verified"
    if record.status == "failed":
        verification_status = "failed"

    return BackupDetailResponse(
        backup_id=record.id,
        case_id=record.case_id,
        manifest=manifest_summary,
        archive_path=record.archive_path,
        verification=BackupVerificationSummary(
            status=verification_status,
            verified_at=record.verified_at,
            errors=errors,
        ),
        warnings=warnings,
    )


def verify_backup(backup_id: str, payload: BackupVerifyRequest) -> BackupVerifyResponse:
    record = _get_backup_record(backup_id)
    verification_warnings: list[str] = []
    missing_files: list[str] = []
    hash_mismatches: list[BackupHashMismatch] = []
    checked_files = 0
    manifest_path = Path(record.manifest_path)
    archive_path = Path(record.archive_path)

    if not manifest_path.exists():
        verification_warnings.append(f"manifest file is missing: {manifest_path}")
    if not archive_path.exists():
        verification_warnings.append(f"archive file is missing: {archive_path}")

    manifest: dict[str, Any] | None = None
    if not verification_warnings:
        try:
            actual_manifest_sha256 = _sha256_file(manifest_path)
            if record.manifest_sha256 and actual_manifest_sha256 != record.manifest_sha256:
                hash_mismatches.append(
                    BackupHashMismatch(
                        relative_path="manifest.json",
                        expected_sha256=record.manifest_sha256,
                        actual_sha256=actual_manifest_sha256,
                    )
            )
            manifest = _read_manifest(manifest_path)
        except BackupError as error:
            verification_warnings.append(str(error))

    if manifest is not None and payload.recompute_archive_hash:
        actual_archive_sha256 = _sha256_file(archive_path)
        expected_archive_sha256 = _string_or_none(_archive_field(manifest, "sha256"))
        if expected_archive_sha256 and actual_archive_sha256 != expected_archive_sha256:
            hash_mismatches.append(
                BackupHashMismatch(
                    relative_path="archive.zip",
                    expected_sha256=expected_archive_sha256,
                    actual_sha256=actual_archive_sha256,
                )
            )
        if record.archive_sha256 and actual_archive_sha256 != record.archive_sha256:
            hash_mismatches.append(
                BackupHashMismatch(
                    relative_path="archive.zip",
                    expected_sha256=record.archive_sha256,
                    actual_sha256=actual_archive_sha256,
                )
            )

    if manifest is not None:
        try:
            zip_warnings, zip_missing, zip_mismatches, checked_files = _verify_zip_members(
                archive_path,
                manifest,
                recompute_hashes=payload.recompute_file_hashes,
            )
            verification_warnings.extend(zip_warnings)
            missing_files.extend(zip_missing)
            hash_mismatches.extend(zip_mismatches)
        except (OSError, zipfile.BadZipFile) as error:
            verification_warnings.append(f"archive could not be read: {error}")

    hash_mismatches = _dedupe_hash_mismatches(hash_mismatches)
    combined_warnings = _dedupe_strings([*record.warnings, *verification_warnings])
    success = not verification_warnings and not missing_files and not hash_mismatches
    status = "verified" if success else "failed"
    verified_at = utc_now_iso() if success else None
    _record_verification_result(
        record=record,
        status=status,
        verified_at=verified_at,
        checked_files=checked_files,
        missing_files=missing_files,
        hash_mismatches=hash_mismatches,
        warnings=combined_warnings,
    )
    return BackupVerifyResponse(
        backup_id=record.id,
        case_id=record.case_id,
        status=status,
        checked_files=checked_files,
        hash_mismatches=hash_mismatches,
        missing_files=missing_files,
        warnings=combined_warnings,
    )


def _build_backup_plan(
    backup_root: str,
    *,
    include_data_dir: bool,
    include_proof_packets: bool,
    require_database: bool,
) -> BackupPlan:
    resolved_backup_root = _resolve_local_path(backup_root, "backup_root")
    db_path = get_db_path().resolve(strict=False)
    data_dir = get_data_dir().resolve(strict=False)
    proof_packets_dir = (data_dir / PROOF_PACKETS_DIRNAME).resolve(strict=False)
    _reject_dangerous_backup_root(resolved_backup_root, data_dir, proof_packets_dir)

    source = BackupSource(
        db_path=str(db_path),
        data_dir=str(data_dir),
        proof_packets_dir=str(proof_packets_dir),
    )
    planned_files: list[PlannedFile] = []
    warnings: list[str] = []

    if not db_path.exists():
        message = f"Configured SQLite DB is missing: {db_path}"
        if require_database:
            raise BackupError(message)
        warnings.append(message)
    elif _is_symlink(db_path):
        message = f"Configured SQLite DB is a symlink and was skipped: {db_path}"
        if require_database:
            raise BackupError(message)
        warnings.append(message)
    elif not db_path.is_file():
        message = f"Configured SQLite DB is not a regular file: {db_path}"
        if require_database:
            raise BackupError(message)
        warnings.append(message)
    else:
        planned_files.append(
            PlannedFile(
                role="sqlite_db",
                relative_path=SQLITE_SNAPSHOT_RELATIVE_PATH,
                source_path=db_path,
                size_bytes=db_path.stat().st_size,
            )
        )

    if include_data_dir:
        planned_files.extend(
            _scan_managed_root(
                root=data_dir,
                role="data_file",
                archive_prefix="data",
                warnings=warnings,
                skip_roots=[proof_packets_dir],
                skip_files=_sqlite_sidecar_paths(db_path),
            )
        )

    if include_proof_packets:
        planned_files.extend(
            _scan_managed_root(
                root=proof_packets_dir,
                role="proof_packet",
                archive_prefix=PROOF_PACKETS_DIRNAME,
                warnings=warnings,
                skip_roots=[],
                skip_files=[],
            )
        )

    return BackupPlan(
        source=source,
        backup_root=resolved_backup_root,
        planned_files=_dedupe_planned_files(planned_files),
        warnings=warnings,
    )


def _scan_managed_root(
    *,
    root: Path,
    role: str,
    archive_prefix: str,
    warnings: list[str],
    skip_roots: list[Path],
    skip_files: list[Path],
) -> list[PlannedFile]:
    if not root.exists():
        warnings.append(f"Managed root is missing: {root}")
        return []
    if _is_symlink(root):
        warnings.append(f"Managed root is a symlink and was skipped: {root}")
        return []
    if not root.is_dir():
        warnings.append(f"Managed root is not a directory: {root}")
        return []

    planned: list[PlannedFile] = []
    stack = [root]
    normalized_skip_roots = [path.resolve(strict=False) for path in skip_roots]
    normalized_skip_files = {str(path.resolve(strict=False)).casefold() for path in skip_files}

    while stack:
        current = stack.pop()
        for child in sorted(current.iterdir(), key=lambda item: str(item).casefold()):
            child_resolved = child.resolve(strict=False)
            if any(_is_at_or_under(child_resolved, skip_root) for skip_root in normalized_skip_roots):
                continue
            if _is_symlink(child):
                warnings.append(f"Skipped symlink: {child}")
                continue
            if child_resolved.is_dir():
                stack.append(child_resolved)
                continue
            if not child_resolved.is_file():
                warnings.append(f"Skipped non-regular file: {child}")
                continue
            if str(child_resolved).casefold() in normalized_skip_files:
                continue
            relative_path = child_resolved.relative_to(root).as_posix()
            planned.append(
                PlannedFile(
                    role=role,
                    relative_path=f"{archive_prefix}/{relative_path}",
                    source_path=child_resolved,
                    size_bytes=child_resolved.stat().st_size,
                )
            )
    return planned


def _record_created_backup(
    *,
    backup_id: str,
    label: str | None,
    archive_path: Path,
    manifest_path: Path,
    manifest_sha256: str,
    archive_sha256: str,
    archive_size_bytes: int,
    file_count: int,
    warnings: list[str],
    created_at: str,
) -> str:
    case_id = new_uuid()
    archive_artifact_id = new_uuid()
    manifest_artifact_id = new_uuid()
    evidence_id = new_uuid()
    title = f"Managed backup: {label or backup_id}"
    summary = "Managed local backup created. Verification is required before trust."
    now = utc_now_iso()

    with connect() as connection:
        connection.execute(
            """
            INSERT INTO cases (id, title, case_type, status, summary, metadata_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                title,
                "managed_backup",
                "open",
                summary,
                dumps_metadata({"workflow": "managed_backup", "backup_id": backup_id}),
                created_at,
                now,
            ),
        )
        _insert_artifact(
            connection,
            artifact_id=archive_artifact_id,
            uri=_path_uri(archive_path),
            name=archive_path.name,
            mime_type="application/zip",
            sha256=archive_sha256,
            size_bytes=archive_size_bytes,
            metadata={
                "role": "backup_archive",
                "workflow": "managed_backup",
                "backup_id": backup_id,
                "path": str(archive_path),
            },
            created_at=created_at,
        )
        _insert_artifact(
            connection,
            artifact_id=manifest_artifact_id,
            uri=_path_uri(manifest_path),
            name=manifest_path.name,
            mime_type="application/json",
            sha256=manifest_sha256,
            size_bytes=manifest_path.stat().st_size,
            metadata={
                "role": "backup_manifest",
                "workflow": "managed_backup",
                "backup_id": backup_id,
                "path": str(manifest_path),
            },
            created_at=created_at,
        )
        _link_artifact(connection, case_id, archive_artifact_id, "primary", created_at)
        _link_artifact(connection, case_id, manifest_artifact_id, "supporting", created_at)
        connection.execute(
            """
            INSERT INTO evidence (
                id, case_id, artifact_id, claim_id, evidence_type, content,
                source_ref, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                evidence_id,
                case_id,
                manifest_artifact_id,
                None,
                "backup_creation",
                f"Managed backup archive created with {file_count} files. Verification not yet run.",
                str(manifest_path),
                dumps_metadata(
                    {
                        "workflow": "managed_backup",
                        "backup_id": backup_id,
                        "warnings": warnings,
                    }
                ),
                created_at,
                created_at,
            ),
        )
        connection.execute(
            """
            INSERT INTO backups (
                id, case_id, label, status, archive_path, manifest_path,
                manifest_sha256, archive_sha256, archive_size_bytes, file_count,
                verified_at, warnings_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                backup_id,
                case_id,
                label,
                "created",
                str(archive_path),
                str(manifest_path),
                manifest_sha256,
                archive_sha256,
                archive_size_bytes,
                file_count,
                None,
                json.dumps(warnings, ensure_ascii=False),
                created_at,
                created_at,
            ),
        )
        connection.commit()
    return case_id


def _record_verification_result(
    *,
    record: BackupRecord,
    status: str,
    verified_at: str | None,
    checked_files: int,
    missing_files: list[str],
    hash_mismatches: list[BackupHashMismatch],
    warnings: list[str],
) -> None:
    now = utc_now_iso()
    with connect() as connection:
        connection.execute(
            """
            UPDATE backups
            SET status = ?, verified_at = ?, warnings_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                verified_at,
                json.dumps(warnings, ensure_ascii=False),
                now,
                record.id,
            ),
        )
        if record.case_id is not None:
            evidence_id = new_uuid()
            connection.execute(
                """
                INSERT INTO evidence (
                    id, case_id, artifact_id, claim_id, evidence_type, content,
                    source_ref, metadata_json, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_id,
                    record.case_id,
                    None,
                    None,
                    "backup_verification",
                    f"Managed backup verification completed with status: {status}.",
                    record.manifest_path,
                    dumps_metadata(
                        {
                            "workflow": "managed_backup",
                            "backup_id": record.id,
                            "status": status,
                            "checked_files": checked_files,
                            "missing_files": missing_files,
                            "hash_mismatches": [item.model_dump() for item in hash_mismatches],
                            "warnings": warnings,
                        }
                    ),
                    now,
                    now,
                ),
            )
            if status == "verified":
                claim_id = new_uuid()
                connection.execute(
                    """
                    INSERT INTO claims (
                        id, case_id, run_id, claim_text, claim_type, status,
                        metadata_json, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        claim_id,
                        record.case_id,
                        None,
                        "Managed backup is complete and hash-verified.",
                        "backup_integrity",
                        "accepted",
                        dumps_metadata(
                            {
                                "workflow": "managed_backup",
                                "backup_id": record.id,
                                "verified_at": verified_at,
                            }
                        ),
                        now,
                        now,
                    ),
                )
                connection.execute(
                    """
                    UPDATE evidence
                    SET claim_id = ?
                    WHERE id = ?
                    """,
                    (claim_id, evidence_id),
                )
        connection.commit()


def _verify_zip_members(
    archive_path: Path,
    manifest: dict[str, Any],
    *,
    recompute_hashes: bool,
) -> tuple[list[str], list[str], list[BackupHashMismatch], int]:
    manifest_files = manifest.get("files")
    if not isinstance(manifest_files, list):
        raise BackupError("manifest files field is missing or invalid")

    warnings: list[str] = []
    missing_files: list[str] = []
    hash_mismatches: list[BackupHashMismatch] = []
    checked_files = 0
    expected_by_path: dict[str, dict[str, Any]] = {}
    for entry in manifest_files:
        if not isinstance(entry, dict):
            warnings.append("Skipped invalid manifest file entry")
            continue
        relative_path = entry.get("relative_path")
        if not isinstance(relative_path, str) or not relative_path:
            warnings.append("Skipped manifest file entry without relative_path")
            continue
        expected_by_path[relative_path] = entry

    with zipfile.ZipFile(archive_path, "r") as archive:
        archive_members = {name for name in archive.namelist() if not name.endswith("/")}
        expected_members = set(expected_by_path)

        for relative_path in sorted(expected_members):
            if relative_path not in archive_members:
                missing_files.append(relative_path)
                continue
            checked_files += 1
            if recompute_hashes:
                actual_sha256 = _sha256_bytes(archive.read(relative_path))
                expected_sha256 = _string_or_none(expected_by_path[relative_path].get("sha256"))
                if expected_sha256 and actual_sha256 != expected_sha256:
                    hash_mismatches.append(
                        BackupHashMismatch(
                            relative_path=relative_path,
                            expected_sha256=expected_sha256,
                            actual_sha256=actual_sha256,
                        )
                    )

        unexpected_members = sorted(archive_members - expected_members)
        for member in unexpected_members:
            warnings.append(f"Unexpected ZIP member: {member}")

    return warnings, missing_files, hash_mismatches, checked_files


def _get_backup_record(backup_id: str) -> BackupRecord:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM backups WHERE id = ?",
            (backup_id,),
        ).fetchone()
    if row is None:
        raise NotFoundError(f"backup not found: {backup_id}")
    return BackupRecord(
        id=row["id"],
        case_id=row["case_id"],
        label=row["label"],
        status=row["status"],
        archive_path=row["archive_path"],
        manifest_path=row["manifest_path"],
        manifest_sha256=row["manifest_sha256"],
        archive_sha256=row["archive_sha256"],
        archive_size_bytes=row["archive_size_bytes"],
        file_count=row["file_count"],
        verified_at=row["verified_at"],
        warnings=_loads_json_list(row["warnings_json"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
        manifest = json.loads(raw)
    except (OSError, json.JSONDecodeError) as error:
        raise BackupError(f"manifest could not be read: {error}") from error
    if not isinstance(manifest, dict):
        raise BackupError("manifest root must be a JSON object")
    return manifest


def _manifest_file_entry(role: str, relative_path: str, path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "role": role,
        "relative_path": relative_path,
        "size_bytes": stat.st_size,
        "sha256": _sha256_file(path),
        "mtime": _mtime_iso(stat.st_mtime),
    }


def _write_archive(
    archive_path: Path,
    staging_dir: Path,
    staged_files: list[dict[str, Any]],
) -> None:
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for entry in staged_files:
            relative_path = entry["relative_path"]
            archive.write(staging_dir / relative_path, arcname=relative_path)


def _snapshot_sqlite_database(source_path: Path, destination_path: Path) -> None:
    source_connection = sqlite3.connect(source_path)
    destination_connection = sqlite3.connect(destination_path)
    try:
        source_connection.backup(destination_connection)
    finally:
        destination_connection.close()
        source_connection.close()


def _insert_artifact(
    connection,
    *,
    artifact_id: str,
    uri: str,
    name: str,
    mime_type: str,
    sha256: str,
    size_bytes: int,
    metadata: dict[str, Any],
    created_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO artifacts (
            id, artifact_type, uri, name, mime_type, sha256, size_bytes,
            metadata_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_id,
            "file",
            uri,
            name,
            mime_type,
            sha256,
            size_bytes,
            dumps_metadata(metadata),
            created_at,
            created_at,
        ),
    )


def _link_artifact(connection, case_id: str, artifact_id: str, role: str, created_at: str) -> None:
    connection.execute(
        """
        INSERT INTO case_artifacts (case_id, artifact_id, role, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (case_id, artifact_id, role, created_at, created_at),
    )


def _resolve_local_path(raw_path: str, label: str) -> Path:
    path = Path(raw_path).expanduser()
    if not str(path).strip():
        raise BackupError(f"{label} is required")
    return path.resolve(strict=False)


def _prepare_backup_root(backup_root: Path) -> None:
    if backup_root.exists():
        if _is_symlink(backup_root):
            raise BackupError("backup_root must not be a symlink")
        if not backup_root.is_dir():
            raise BackupError("backup_root must be a directory")
    backup_root.mkdir(parents=True, exist_ok=True)


def _remove_generated_outputs(*paths: Path) -> None:
    for path in paths:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def _reject_dangerous_backup_root(backup_root: Path, data_dir: Path, proof_packets_dir: Path) -> None:
    if _is_at_or_under(backup_root, data_dir):
        raise BackupError("backup_root must not be inside the live ProofFlow data_dir")
    if _is_at_or_under(backup_root, proof_packets_dir):
        raise BackupError("backup_root must not be inside the live proof_packets directory")


def _sqlite_sidecar_paths(db_path: Path) -> list[Path]:
    return [
        db_path,
        Path(f"{db_path}-wal").resolve(strict=False),
        Path(f"{db_path}-shm").resolve(strict=False),
    ]


def _dedupe_planned_files(files: list[PlannedFile]) -> list[PlannedFile]:
    deduped: list[PlannedFile] = []
    seen: set[str] = set()
    for planned_file in files:
        key = planned_file.relative_path.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(planned_file)
    return deduped


def _dedupe_strings(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped


def _dedupe_hash_mismatches(mismatches: list[BackupHashMismatch]) -> list[BackupHashMismatch]:
    deduped: list[BackupHashMismatch] = []
    seen: set[tuple[str, str | None, str | None]] = set()
    for mismatch in mismatches:
        key = (mismatch.relative_path, mismatch.expected_sha256, mismatch.actual_sha256)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(mismatch)
    return deduped


def _is_at_or_under(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except ValueError:
        return False


def _is_symlink(path: Path) -> bool:
    try:
        return path.is_symlink()
    except OSError:
        return False


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _loads_json_list(raw_json: str | None) -> list[str]:
    if not raw_json:
        return []
    try:
        value = json.loads(raw_json)
    except json.JSONDecodeError:
        return [f"invalid warnings_json: {raw_json}"]
    if not isinstance(value, list):
        return [f"invalid warnings_json type: {type(value).__name__}"]
    return [str(item) for item in value]


def _archive_field(manifest: dict[str, Any], field_name: str) -> Any:
    archive = manifest.get("archive")
    if not isinstance(archive, dict):
        return None
    return archive.get(field_name)


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _path_uri(path: Path) -> str:
    return path.resolve(strict=False).as_uri()


def _mtime_iso(timestamp: float) -> str:
    from datetime import UTC, datetime

    return datetime.fromtimestamp(timestamp, tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _new_backup_id() -> str:
    from datetime import UTC, datetime

    timestamp = datetime.now(tz=UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"backup-{timestamp}-{new_uuid()[:8]}"
