import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from proofflow.db import connect
from proofflow.migrations import init_db
from proofflow.models.schemas import (
    BackupCreateRequest,
    BackupPreviewRequest,
    BackupVerifyRequest,
)
from proofflow.services import backup_service
from proofflow.services.backup_service import (
    BackupError,
    create_backup,
    preview_backup,
    verify_backup,
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


def _count_rows(table_name: str) -> int:
    with connect() as connection:
        return connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()["count"]


def _seed_managed_files(data_dir: Path) -> None:
    (data_dir / "notes").mkdir(parents=True, exist_ok=True)
    (data_dir / "notes" / "review.txt").write_text("review evidence", encoding="utf-8")
    (data_dir / "proof_packets" / "packet.md").write_text("# Packet\n", encoding="utf-8")


def _load_manifest(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _rewrite_zip_member(archive_path: Path, target: str, content: bytes) -> None:
    with zipfile.ZipFile(archive_path, "r") as archive:
        entries = {
            name: archive.read(name)
            for name in archive.namelist()
            if not name.endswith("/")
        }
    entries[target] = content
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, body in entries.items():
            archive.writestr(name, body)


def test_preview_is_read_only_and_rejects_backup_root_inside_data_dir(monkeypatch, tmp_path):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)

    response = preview_backup(BackupPreviewRequest(backup_root=str(backup_root)))

    assert not backup_root.exists()
    assert _count_rows("backups") == 0
    assert _count_rows("cases") == 0
    assert any(file.role == "sqlite_db" for file in response.planned_files)
    with pytest.raises(BackupError, match="data_dir"):
        preview_backup(BackupPreviewRequest(backup_root=str(data_dir / "nested-backups")))


def test_create_backup_writes_manifest_archive_case_artifacts_and_skips_source_roots(
    monkeypatch,
    tmp_path,
):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    localproof_source = tmp_path / "localproof-source"
    localproof_source.mkdir()
    (localproof_source / "do-not-archive.txt").write_text("outside", encoding="utf-8")

    response = create_backup(
        BackupCreateRequest(
            backup_root=str(backup_root),
            label="before-next-sprint",
        )
    )

    archive_path = Path(response.archive_path)
    manifest_path = Path(response.manifest_path)
    assert archive_path.exists()
    assert manifest_path.exists()
    assert response.archive_sha256
    assert response.manifest_sha256

    manifest = _load_manifest(response.manifest_path)
    for field in (
        "manifest_version",
        "app_name",
        "app_version",
        "schema_version",
        "created_at",
        "backup_id",
        "source",
        "files",
        "archive",
        "warnings",
    ):
        assert field in manifest
    assert manifest["archive"]["sha256"] == response.archive_sha256
    assert manifest["archive"]["size_bytes"] == archive_path.stat().st_size

    with zipfile.ZipFile(archive_path, "r") as archive:
        names = set(archive.namelist())
    assert "db/proofflow.db" in names
    assert "data/notes/review.txt" in names
    assert "proof_packets/packet.md" in names
    assert "data/proofflow.db" not in names
    assert "localproof-source/do-not-archive.txt" not in names

    with connect() as connection:
        backup_row = connection.execute("SELECT * FROM backups WHERE id = ?", (response.backup_id,)).fetchone()
        case_row = connection.execute("SELECT * FROM cases WHERE id = ?", (response.case_id,)).fetchone()
        artifact_count = connection.execute(
            "SELECT COUNT(*) AS count FROM case_artifacts WHERE case_id = ?",
            (response.case_id,),
        ).fetchone()["count"]
        evidence_count = connection.execute(
            "SELECT COUNT(*) AS count FROM evidence WHERE case_id = ?",
            (response.case_id,),
        ).fetchone()["count"]
    assert backup_row["status"] == "created"
    assert backup_row["archive_sha256"] == response.archive_sha256
    assert backup_row["manifest_sha256"] == response.manifest_sha256
    assert case_row["case_type"] == "managed_backup"
    assert artifact_count == 2
    assert evidence_count == 1


def test_create_backup_cleans_generated_outputs_when_metadata_recording_fails(
    monkeypatch,
    tmp_path,
):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)

    def fail_recording(**_kwargs):
        raise BackupError("simulated metadata failure")

    monkeypatch.setattr(backup_service, "_record_created_backup", fail_recording)

    with pytest.raises(BackupError, match="simulated metadata failure"):
        create_backup(BackupCreateRequest(backup_root=str(backup_root)))

    assert not list(backup_root.glob("*.zip"))
    assert not list(backup_root.glob("*.manifest.json"))
    assert not any(backup_root.glob(".proofflow-backup-staging-*"))
    assert _count_rows("backups") == 0
    assert _count_rows("cases") == 0
    assert _count_rows("artifacts") == 0
    assert _count_rows("evidence") == 0


def test_verify_fresh_backup_updates_status_verified_and_claim(monkeypatch, tmp_path):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    created = create_backup(BackupCreateRequest(backup_root=str(backup_root)))

    verified = verify_backup(created.backup_id, BackupVerifyRequest())

    assert verified.status == "verified"
    assert verified.checked_files >= 3
    assert verified.hash_mismatches == []
    assert verified.missing_files == []
    with connect() as connection:
        row = connection.execute("SELECT status, verified_at FROM backups WHERE id = ?", (created.backup_id,)).fetchone()
        claim_count = connection.execute(
            "SELECT COUNT(*) AS count FROM claims WHERE case_id = ? AND claim_type = ?",
            (created.case_id, "backup_integrity"),
        ).fetchone()["count"]
    assert row["status"] == "verified"
    assert row["verified_at"] is not None
    assert claim_count == 1


def test_verify_fails_when_archive_or_manifest_is_missing(monkeypatch, tmp_path):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    missing_archive = create_backup(BackupCreateRequest(backup_root=str(backup_root)))
    Path(missing_archive.archive_path).unlink()

    archive_result = verify_backup(missing_archive.backup_id, BackupVerifyRequest())

    assert archive_result.status == "failed"
    assert any("archive file is missing" in warning for warning in archive_result.warnings)

    missing_manifest = create_backup(BackupCreateRequest(backup_root=str(backup_root)))
    Path(missing_manifest.manifest_path).unlink()

    manifest_result = verify_backup(missing_manifest.backup_id, BackupVerifyRequest())

    assert manifest_result.status == "failed"
    assert any("manifest file is missing" in warning for warning in manifest_result.warnings)


def test_verify_fails_on_zip_member_hash_mismatch(monkeypatch, tmp_path):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    created = create_backup(BackupCreateRequest(backup_root=str(backup_root)))

    _rewrite_zip_member(Path(created.archive_path), "data/notes/review.txt", b"tampered")
    result = verify_backup(created.backup_id, BackupVerifyRequest())

    assert result.status == "failed"
    archive_mismatches = [
        mismatch
        for mismatch in result.hash_mismatches
        if mismatch.relative_path == "archive.zip"
    ]
    assert len(archive_mismatches) == 1
    assert any(mismatch.relative_path == "data/notes/review.txt" for mismatch in result.hash_mismatches)
    with connect() as connection:
        status = connection.execute("SELECT status FROM backups WHERE id = ?", (created.backup_id,)).fetchone()["status"]
    assert status == "failed"


def test_symlink_files_and_dirs_are_skipped(monkeypatch, tmp_path):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside", encoding="utf-8")
    outside_dir = tmp_path / "outside-dir"
    outside_dir.mkdir()
    file_link = data_dir / "linked-file.txt"
    dir_link = data_dir / "linked-dir"
    try:
        file_link.symlink_to(outside_file)
        dir_link.symlink_to(outside_dir, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"symlink creation is not available in this environment: {error}")

    response = preview_backup(BackupPreviewRequest(backup_root=str(backup_root)))

    planned_paths = {file.relative_path for file in response.planned_files}
    assert "data/linked-file.txt" not in planned_paths
    assert "data/linked-dir" not in planned_paths
    assert any("Skipped symlink" in warning for warning in response.warnings)


def test_sqlite_snapshot_is_valid_database(monkeypatch, tmp_path):
    _db_path, data_dir, backup_root = _init_temp_instance(monkeypatch, tmp_path)
    _seed_managed_files(data_dir)
    created = create_backup(BackupCreateRequest(backup_root=str(backup_root)))
    snapshot_path = tmp_path / "snapshot.db"

    with zipfile.ZipFile(created.archive_path, "r") as archive:
        snapshot_path.write_bytes(archive.read("db/proofflow.db"))

    with sqlite3.connect(snapshot_path) as connection:
        case_count = connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0]

    assert case_count == 0
