import hashlib
import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from proofflow.db import connect
from proofflow.migrations import init_db
from proofflow.models.schemas import (
    BackupCreateRequest,
    BackupVerifyRequest,
    RestorePreviewRequest,
    RestoreToNewLocationRequest,
)
from proofflow.services.backup_service import create_backup, verify_backup
from proofflow.services.errors import NotFoundError
from proofflow.services import restore_service
from proofflow.services.restore_service import (
    RestoreError,
    preview_restore,
    restore_to_new_location,
)


def _init_temp_instance(monkeypatch, tmp_path: Path) -> tuple[Path, Path, Path]:
    data_dir = tmp_path / "data"
    db_path = data_dir / "proofflow.db"
    backup_root = tmp_path / "backups"
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(db_path))
    monkeypatch.setenv("PROOFFLOW_DATA_DIR", str(data_dir))
    init_db()
    (data_dir / "proof_packets").mkdir(parents=True, exist_ok=True)
    return db_path, data_dir, backup_root


def _seed_managed_files(data_dir: Path) -> None:
    (data_dir / "notes").mkdir(parents=True, exist_ok=True)
    (data_dir / "notes" / "review.txt").write_text("review evidence", encoding="utf-8")
    (data_dir / "proof_packets" / "packet.md").write_text("# Packet\n", encoding="utf-8")


def _make_verified_backup(backup_root: Path) -> str:
    created = create_backup(BackupCreateRequest(backup_root=str(backup_root)))
    verified = verify_backup(created.backup_id, BackupVerifyRequest())
    assert verified.status == "verified"
    return created.backup_id


def _restore_targets(tmp_path: Path, name: str = "restore") -> tuple[Path, Path]:
    restore_root = tmp_path / name
    return restore_root / "proofflow.db", restore_root / "data"


def _count_rows(table_name: str) -> int:
    with connect() as connection:
        return connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()["count"]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _backup_paths(backup_id: str) -> tuple[Path, Path]:
    with connect() as connection:
        row = connection.execute(
            "SELECT archive_path, manifest_path FROM backups WHERE id = ?",
            (backup_id,),
        ).fetchone()
    return Path(row["archive_path"]), Path(row["manifest_path"])


def _write_manifest_and_update_record(backup_id: str, manifest: dict) -> None:
    archive_path, manifest_path = _backup_paths(backup_id)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with connect() as connection:
        connection.execute(
            """
            UPDATE backups
            SET manifest_sha256 = ?, archive_sha256 = ?
            WHERE id = ?
            """,
            (_sha256_file(manifest_path), _sha256_file(archive_path), backup_id),
        )
        connection.commit()


def _load_manifest(backup_id: str) -> dict:
    _archive_path, manifest_path = _backup_paths(backup_id)
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _rewrite_zip(archive_path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)


def _archive_entries(archive_path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(archive_path, "r") as archive:
        return {
            name: archive.read(name)
            for name in archive.namelist()
            if not name.endswith("/")
        }


def _add_manifest_file(backup_id: str, relative_path: str, content: bytes, role: str = "data_file") -> None:
    archive_path, _manifest_path = _backup_paths(backup_id)
    entries = _archive_entries(archive_path)
    entries[relative_path] = content
    _rewrite_zip(archive_path, entries)
    manifest = _load_manifest(backup_id)
    manifest["files"].append(
        {
            "role": role,
            "relative_path": relative_path,
            "size_bytes": len(content),
            "sha256": _sha256_bytes(content),
            "mtime": "2026-04-28T00:00:00Z",
        }
    )
    manifest["archive"]["sha256"] = _sha256_file(archive_path)
    manifest["archive"]["size_bytes"] = archive_path.stat().st_size
    _write_manifest_and_update_record(backup_id, manifest)


def _create_dir_symlink_or_skip(link_path: Path, target_path: Path) -> None:
    target_path.mkdir(parents=True, exist_ok=True)
    try:
        link_path.symlink_to(target_path, target_is_directory=True)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"directory symlink unavailable on this system: {error}")


def _preview_payload(backup_id: str, target_db_path: Path, target_data_dir: Path) -> RestorePreviewRequest:
    return RestorePreviewRequest(
        backup_id=backup_id,
        target_db_path=str(target_db_path),
        target_data_dir=str(target_data_dir),
    )


def test_restore_preview_requires_verified_backup_and_records_evidence(monkeypatch, tmp_path):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    unverified = create_backup(BackupCreateRequest(backup_root=str(backup_root)))
    target_db_path, target_data_dir = _restore_targets(tmp_path)

    with pytest.raises(RestoreError, match="verified"):
        preview_restore(_preview_payload(unverified.backup_id, target_db_path, target_data_dir))

    verify_backup(unverified.backup_id, BackupVerifyRequest())
    before_evidence = _count_rows("evidence")
    preview = preview_restore(_preview_payload(unverified.backup_id, target_db_path, target_data_dir))

    assert preview.restore_preview_id
    assert preview.plan_hash
    assert preview.verified is True
    assert not target_db_path.exists()
    assert not target_data_dir.exists()
    assert _count_rows("restore_previews") == 1
    assert _count_rows("evidence") == before_evidence + 1


def test_restore_preview_rejects_live_targets_and_reports_overwrites(monkeypatch, tmp_path):
    db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    backup_id = _make_verified_backup(backup_root)
    target_db_path, target_data_dir = _restore_targets(tmp_path)

    with pytest.raises(RestoreError, match="PROOFFLOW_DB_PATH"):
        preview_restore(_preview_payload(backup_id, db_path, target_data_dir))
    with pytest.raises(RestoreError, match="PROOFFLOW_DATA_DIR"):
        preview_restore(_preview_payload(backup_id, target_db_path, data_dir))
    with pytest.raises(RestoreError, match="managed data roots"):
        preview_restore(_preview_payload(backup_id, data_dir / "nested.db", target_data_dir))
    with pytest.raises(RestoreError, match="managed data roots"):
        preview_restore(_preview_payload(backup_id, target_db_path, data_dir / "proof_packets" / "inspect"))
    with pytest.raises(RestoreError, match="target_db_path"):
        preview_restore(_preview_payload(backup_id, target_data_dir / "proofflow.db", target_data_dir))

    target_db_path.parent.mkdir(parents=True)
    target_db_path.write_text("existing db", encoding="utf-8")
    (target_data_dir / "notes").mkdir(parents=True)
    (target_data_dir / "notes" / "review.txt").write_text("existing", encoding="utf-8")
    preview = preview_restore(_preview_payload(backup_id, target_db_path, target_data_dir))

    overwrites = [write for write in preview.planned_writes if write.would_overwrite]
    assert {Path(write.target_path).name for write in overwrites} >= {"proofflow.db", "review.txt"}


def test_restore_preview_rejects_unsafe_parent_chain(monkeypatch, tmp_path):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    backup_id = _make_verified_backup(backup_root)
    target_db_path, target_data_dir = _restore_targets(tmp_path)
    blocking_parent = tmp_path / "not-a-directory"
    blocking_parent.write_text("file", encoding="utf-8")

    with pytest.raises(RestoreError, match="parent is not a directory"):
        preview_restore(_preview_payload(backup_id, blocking_parent / "proofflow.db", target_data_dir))

    link_path = tmp_path / "linked-parent"
    _create_dir_symlink_or_skip(link_path, tmp_path / "linked-real")
    with pytest.raises(RestoreError, match="symlink or junction"):
        preview_restore(_preview_payload(backup_id, link_path / "proofflow.db", target_data_dir))


def test_restore_preview_reports_version_and_schema_risks_and_blocks_missing_metadata(
    monkeypatch,
    tmp_path,
):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    backup_id = _make_verified_backup(backup_root)
    target_db_path, target_data_dir = _restore_targets(tmp_path)
    manifest = _load_manifest(backup_id)
    manifest["app_version"] = "0.0.0-old"
    manifest["schema_version"] = "legacy"
    _write_manifest_and_update_record(backup_id, manifest)

    preview = preview_restore(_preview_payload(backup_id, target_db_path, target_data_dir))

    assert [risk.code for risk in preview.version_risks] == ["app_version_mismatch"]
    assert [risk.code for risk in preview.schema_risks] == ["schema_version_mismatch"]

    missing_app_version = dict(manifest)
    missing_app_version.pop("app_version")
    _write_manifest_and_update_record(backup_id, missing_app_version)
    with pytest.raises(RestoreError, match="app_version"):
        preview_restore(_preview_payload(backup_id, target_db_path, target_data_dir))

    missing_schema_version = dict(manifest)
    missing_schema_version.pop("schema_version")
    _write_manifest_and_update_record(backup_id, missing_schema_version)
    with pytest.raises(RestoreError, match="schema_version"):
        preview_restore(_preview_payload(backup_id, target_db_path, target_data_dir))


def test_restore_preview_rejects_missing_archive_and_hash_mismatch(monkeypatch, tmp_path):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    backup_id = _make_verified_backup(backup_root)
    target_db_path, target_data_dir = _restore_targets(tmp_path)
    _archive_path, manifest_path = _backup_paths(backup_id)

    manifest_path.unlink()
    with pytest.raises(RestoreError, match="manifest file is missing"):
        preview_restore(_preview_payload(backup_id, target_db_path, target_data_dir))

    backup_id = _make_verified_backup(backup_root)
    archive_path, _manifest_path = _backup_paths(backup_id)
    archive_path.unlink()
    with pytest.raises(RestoreError, match="archive file is missing"):
        preview_restore(_preview_payload(backup_id, target_db_path, target_data_dir))

    backup_id = _make_verified_backup(backup_root)
    archive_path, _manifest_path = _backup_paths(backup_id)
    entries = _archive_entries(archive_path)
    entries["data/notes/review.txt"] = b"tampered"
    _rewrite_zip(archive_path, entries)

    with pytest.raises(RestoreError, match="hash_mismatches"):
        preview_restore(_preview_payload(backup_id, target_db_path, target_data_dir))


def test_restore_to_new_location_rejects_missing_unknown_or_mismatched_preview(
    monkeypatch,
    tmp_path,
):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    first_backup = _make_verified_backup(backup_root)
    second_backup = _make_verified_backup(backup_root)
    target_db_path, target_data_dir = _restore_targets(tmp_path)
    preview = preview_restore(_preview_payload(first_backup, target_db_path, target_data_dir))

    with pytest.raises(NotFoundError):
        restore_to_new_location(
            RestoreToNewLocationRequest(
                backup_id=first_backup,
                target_db_path=str(target_db_path),
                target_data_dir=str(target_data_dir),
                accepted_preview_id="missing",
            )
        )
    with pytest.raises(RestoreError, match="different backup_id"):
        restore_to_new_location(
            RestoreToNewLocationRequest(
                backup_id=second_backup,
                target_db_path=str(target_db_path),
                target_data_dir=str(target_data_dir),
                accepted_preview_id=preview.restore_preview_id,
            )
        )
    with pytest.raises(RestoreError, match="target_db_path"):
        restore_to_new_location(
            RestoreToNewLocationRequest(
                backup_id=first_backup,
                target_db_path=str(tmp_path / "other" / "proofflow.db"),
                target_data_dir=str(target_data_dir),
                accepted_preview_id=preview.restore_preview_id,
            )
        )


def test_restore_to_new_location_rejects_stale_preview_and_overwrites(monkeypatch, tmp_path):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    backup_id = _make_verified_backup(backup_root)
    target_db_path, target_data_dir = _restore_targets(tmp_path)
    preview = preview_restore(_preview_payload(backup_id, target_db_path, target_data_dir))
    (target_data_dir / "notes").mkdir(parents=True)
    (target_data_dir / "notes" / "review.txt").write_text("changed", encoding="utf-8")

    with pytest.raises(RestoreError, match="stale"):
        restore_to_new_location(
            RestoreToNewLocationRequest(
                backup_id=backup_id,
                target_db_path=str(target_db_path),
                target_data_dir=str(target_data_dir),
                accepted_preview_id=preview.restore_preview_id,
            )
        )

    overwrite_db_path, overwrite_data_dir = _restore_targets(tmp_path, "overwrite")
    overwrite_db_path.parent.mkdir(parents=True)
    overwrite_db_path.write_text("existing", encoding="utf-8")
    overwrite_preview = preview_restore(_preview_payload(backup_id, overwrite_db_path, overwrite_data_dir))
    with pytest.raises(RestoreError, match="overwrite"):
        restore_to_new_location(
            RestoreToNewLocationRequest(
                backup_id=backup_id,
                target_db_path=str(overwrite_db_path),
                target_data_dir=str(overwrite_data_dir),
                accepted_preview_id=overwrite_preview.restore_preview_id,
            )
        )


def test_restore_to_new_location_rejects_symlink_parent_after_preview(monkeypatch, tmp_path):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    backup_id = _make_verified_backup(backup_root)
    target_root = tmp_path / "restore-link"
    target_db_path = target_root / "proofflow.db"
    target_data_dir = target_root / "data"
    preview = preview_restore(_preview_payload(backup_id, target_db_path, target_data_dir))

    _create_dir_symlink_or_skip(target_root, tmp_path / "restore-real")

    with pytest.raises(RestoreError, match="symlink or junction"):
        restore_to_new_location(
            RestoreToNewLocationRequest(
                backup_id=backup_id,
                target_db_path=str(target_db_path),
                target_data_dir=str(target_data_dir),
                accepted_preview_id=preview.restore_preview_id,
            )
        )


def test_restore_to_new_location_rechecks_link_like_parent_after_preview(monkeypatch, tmp_path):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    backup_id = _make_verified_backup(backup_root)
    target_root = tmp_path / "restore-junction-window"
    target_db_path = target_root / "proofflow.db"
    target_data_dir = target_root / "data"
    preview = preview_restore(_preview_payload(backup_id, target_db_path, target_data_dir))

    original_is_link_like = restore_service._is_link_like

    def _fake_is_link_like(path: Path) -> bool:
        if path == target_root:
            return True
        return original_is_link_like(path)

    monkeypatch.setattr(restore_service, "_is_link_like", _fake_is_link_like)

    with pytest.raises(RestoreError, match="symlink or junction"):
        restore_to_new_location(
            RestoreToNewLocationRequest(
                backup_id=backup_id,
                target_db_path=str(target_db_path),
                target_data_dir=str(target_data_dir),
                accepted_preview_id=preview.restore_preview_id,
            )
        )


def test_restore_to_new_location_restores_files_records_evidence_and_db_opens(
    monkeypatch,
    tmp_path,
):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    backup_id = _make_verified_backup(backup_root)
    target_db_path, target_data_dir = _restore_targets(tmp_path)
    preview = preview_restore(_preview_payload(backup_id, target_db_path, target_data_dir))
    before_evidence = _count_rows("evidence")

    restored = restore_to_new_location(
        RestoreToNewLocationRequest(
            backup_id=backup_id,
            target_db_path=str(target_db_path),
            target_data_dir=str(target_data_dir),
            accepted_preview_id=preview.restore_preview_id,
        )
    )

    assert restored.status == "restored_to_new_location"
    assert restored.restored_files == len(preview.planned_writes)
    assert target_db_path.exists()
    assert (target_data_dir / "notes" / "review.txt").read_text(encoding="utf-8") == "review evidence"
    assert (target_data_dir / "proof_packets" / "packet.md").read_text(encoding="utf-8") == "# Packet\n"
    with sqlite3.connect(target_db_path) as connection:
        table_count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'cases'"
        ).fetchone()[0]
    assert table_count == 1
    assert _count_rows("evidence") == before_evidence + 1


def test_restore_rejects_zip_slip_and_does_not_extract_unexpected_members(monkeypatch, tmp_path):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    backup_id = _make_verified_backup(backup_root)
    archive_path, _manifest_path = _backup_paths(backup_id)
    manifest = _load_manifest(backup_id)
    entries = _archive_entries(archive_path)
    entries["../evil.txt"] = b"evil"
    _rewrite_zip(archive_path, entries)
    manifest["files"].append(
        {
            "role": "data_file",
            "relative_path": "../evil.txt",
            "size_bytes": 4,
            "sha256": _sha256_bytes(b"evil"),
            "mtime": "2026-04-28T00:00:00Z",
        }
    )
    manifest["archive"]["sha256"] = _sha256_file(archive_path)
    manifest["archive"]["size_bytes"] = archive_path.stat().st_size
    _write_manifest_and_update_record(backup_id, manifest)
    target_db_path, target_data_dir = _restore_targets(tmp_path)

    with pytest.raises(RestoreError, match="unsafe archive member"):
        preview_restore(_preview_payload(backup_id, target_db_path, target_data_dir))

    backup_id = _make_verified_backup(backup_root)
    target_db_path, target_data_dir = _restore_targets(tmp_path, "localproof-source")
    _add_manifest_file(backup_id, "localproof-source/work/file.txt", b"source file")

    with pytest.raises(RestoreError, match="unsupported archive member"):
        preview_restore(_preview_payload(backup_id, target_db_path, target_data_dir))

    backup_id = _make_verified_backup(backup_root)
    archive_path, _manifest_path = _backup_paths(backup_id)
    target_db_path, target_data_dir = _restore_targets(tmp_path, "unexpected")
    preview = preview_restore(_preview_payload(backup_id, target_db_path, target_data_dir))
    entries = _archive_entries(archive_path)
    entries["unexpected.txt"] = b"do not write"
    _rewrite_zip(archive_path, entries)

    with pytest.raises(RestoreError):
        restore_to_new_location(
            RestoreToNewLocationRequest(
                backup_id=backup_id,
                target_db_path=str(target_db_path),
                target_data_dir=str(target_data_dir),
                accepted_preview_id=preview.restore_preview_id,
            )
        )
    assert not (target_data_dir / "unexpected.txt").exists()


def test_restore_cleans_created_files_on_failed_write(monkeypatch, tmp_path):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    backup_id = _make_verified_backup(backup_root)
    target_db_path, target_data_dir = _restore_targets(tmp_path)
    preview = preview_restore(_preview_payload(backup_id, target_db_path, target_data_dir))
    original_write = restore_service._write_restore_file
    calls = {"count": 0}

    def fail_after_first_write(target_path, content, created_files, created_dirs):
        calls["count"] += 1
        if calls["count"] == 1:
            original_write(target_path, content, created_files, created_dirs)
            return
        raise RestoreError("simulated restore write failure")

    monkeypatch.setattr(restore_service, "_write_restore_file", fail_after_first_write)

    with pytest.raises(RestoreError, match="simulated"):
        restore_to_new_location(
            RestoreToNewLocationRequest(
                backup_id=backup_id,
                target_db_path=str(target_db_path),
                target_data_dir=str(target_data_dir),
                accepted_preview_id=preview.restore_preview_id,
            )
        )

    assert not target_db_path.exists()
    assert not target_data_dir.exists()


def test_restore_to_new_location_succeeds_with_warning_when_evidence_recording_fails(
    monkeypatch,
    tmp_path,
):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    backup_id = _make_verified_backup(backup_root)
    target_db_path, target_data_dir = _restore_targets(tmp_path)
    preview = preview_restore(_preview_payload(backup_id, target_db_path, target_data_dir))

    def fail_record_result(*_args, **_kwargs):
        raise RuntimeError("simulated evidence failure")

    monkeypatch.setattr(restore_service, "_record_restore_result", fail_record_result)

    restored = restore_to_new_location(
        RestoreToNewLocationRequest(
            backup_id=backup_id,
            target_db_path=str(target_db_path),
            target_data_dir=str(target_data_dir),
            accepted_preview_id=preview.restore_preview_id,
        )
    )

    assert restored.status == "restored_to_new_location"
    assert target_db_path.exists()
    assert (target_data_dir / "notes" / "review.txt").exists()
    assert any("evidence could not be recorded" in warning for warning in restored.warnings)
