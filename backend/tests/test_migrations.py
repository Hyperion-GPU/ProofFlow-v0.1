import sqlite3

import pytest

from proofflow.db import connect
from proofflow.migrations import init_db


CORE_TABLES = {
    "cases",
    "artifacts",
    "case_artifacts",
    "artifact_text_chunks",
    "artifact_text_fts",
    "runs",
    "claims",
    "evidence",
    "actions",
    "decisions",
}


def test_init_db_creates_core_tables_and_is_idempotent(tmp_path):
    db_path = tmp_path / "nested" / "proofflow.db"

    resolved_path = init_db(str(db_path))
    init_db(str(db_path))

    assert resolved_path == db_path.resolve()
    assert db_path.exists()

    with connect(resolved_path) as connection:
        foreign_keys = connection.execute("PRAGMA foreign_keys").fetchone()[0]
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()

    table_names = {row["name"] for row in rows}

    assert foreign_keys == 1
    assert CORE_TABLES.issubset(table_names)


def test_init_db_adds_action_columns_to_existing_database(tmp_path):
    db_path = tmp_path / "legacy-actions.db"
    with connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE actions (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                run_id TEXT,
                action_type TEXT NOT NULL,
                status TEXT NOT NULL,
                description TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.commit()

    init_db(str(db_path))

    with connect(db_path) as connection:
        action_columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(actions)")
        }

    assert {
        "title",
        "reason",
        "preview_json",
        "result_json",
        "undo_json",
    }.issubset(action_columns)


def test_init_db_rebuilds_legacy_decisions_table(tmp_path):
    db_path = tmp_path / "legacy-decisions.db"
    with connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE cases (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                case_type TEXT NOT NULL,
                status TEXT NOT NULL,
                summary TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE actions (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                run_id TEXT,
                action_type TEXT NOT NULL,
                status TEXT NOT NULL,
                description TEXT NOT NULL,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE decisions (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                action_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                rationale TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
                FOREIGN KEY (action_id) REFERENCES actions(id) ON DELETE CASCADE
            )
            """
        )
        connection.execute(
            """
            INSERT INTO cases (
                id, title, case_type, status, summary, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "case-1",
                "Legacy case",
                "local_proof",
                "open",
                None,
                "{}",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO actions (
                id, case_id, run_id, action_type, status, description,
                metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "action-1",
                "case-1",
                None,
                "manual_check",
                "previewed",
                "Legacy action",
                "{}",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:00:00Z",
            ),
        )
        connection.execute(
            """
            INSERT INTO decisions (
                id, case_id, action_id, decision, rationale,
                metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "decision-1",
                "case-1",
                "action-1",
                "Accept legacy action",
                "Legacy rationale",
                '{"legacy":true}',
                "2026-01-02T00:00:00Z",
                "2026-01-02T00:00:00Z",
            ),
        )
        connection.commit()

    init_db(str(db_path))

    with connect(db_path) as connection:
        decision_columns = {
            row["name"]: row for row in connection.execute("PRAGMA table_info(decisions)")
        }
        migrated = connection.execute(
            """
            SELECT id, case_id, title, status, rationale, result, metadata_json
            FROM decisions
            WHERE id = ?
            """,
            ("decision-1",),
        ).fetchone()
        connection.execute(
            """
            INSERT INTO decisions (
                id, case_id, title, status, rationale, result,
                metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "decision-2",
                "case-1",
                "New case-only decision",
                "proposed",
                "No action is required.",
                "Record the case decision.",
                "{}",
                "2026-01-03T00:00:00Z",
                "2026-01-03T00:00:00Z",
            ),
        )
        connection.commit()

    assert "action_id" not in decision_columns
    assert {"title", "status", "result"}.issubset(decision_columns)
    assert migrated["title"] == "Accept legacy action"
    assert migrated["status"] == "accepted"
    assert migrated["rationale"] == "Legacy rationale"
    assert migrated["result"] == "Accept legacy action"
    assert migrated["metadata_json"] == '{"legacy":true}'


def test_init_db_removes_restore_preview_backup_delete_cascade(tmp_path):
    db_path = tmp_path / "legacy-restore-preview-cascade.db"
    with connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE cases (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                case_type TEXT NOT NULL,
                status TEXT NOT NULL,
                summary TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE backups (
                id TEXT PRIMARY KEY,
                case_id TEXT,
                label TEXT,
                status TEXT NOT NULL,
                archive_path TEXT NOT NULL,
                manifest_path TEXT NOT NULL,
                manifest_sha256 TEXT,
                archive_sha256 TEXT,
                archive_size_bytes INTEGER,
                file_count INTEGER,
                verified_at TEXT,
                warnings_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE restore_previews (
                id TEXT PRIMARY KEY,
                backup_id TEXT NOT NULL,
                case_id TEXT,
                target_db_path TEXT NOT NULL,
                target_data_dir TEXT NOT NULL,
                plan_hash TEXT NOT NULL,
                archive_sha256 TEXT,
                manifest_sha256 TEXT,
                planned_writes_json TEXT NOT NULL,
                schema_risks_json TEXT NOT NULL DEFAULT '[]',
                version_risks_json TEXT NOT NULL DEFAULT '[]',
                warnings_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (backup_id) REFERENCES backups(id) ON DELETE CASCADE,
                FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL
            )
            """
        )
        connection.execute(
            """
            INSERT INTO cases (
                id, title, case_type, status, summary, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("case-1", "Case", "managed_backup", "open", None, "{}", "now", "now"),
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
                "backup-1",
                "case-1",
                None,
                "verified",
                "backup.zip",
                "manifest.json",
                "manifest-sha",
                "archive-sha",
                1,
                1,
                "now",
                "[]",
                "now",
                "now",
            ),
        )
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
                "preview-1",
                "backup-1",
                "case-1",
                "restore.db",
                "restore-data",
                "plan-hash",
                "archive-sha",
                "manifest-sha",
                "[]",
                "[]",
                "[]",
                "[]",
                "now",
                "now",
            ),
        )
        connection.commit()

    init_db(str(db_path))

    with connect(db_path) as connection:
        backup_fk = [
            row
            for row in connection.execute("PRAGMA foreign_key_list(restore_previews)")
            if row["table"] == "backups" and row["from"] == "backup_id"
        ]
        preview_count = connection.execute(
            "SELECT COUNT(*) FROM restore_previews WHERE id = ?",
            ("preview-1",),
        ).fetchone()[0]
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM backups WHERE id = ?", ("backup-1",))
            connection.commit()

    assert [row["on_delete"] for row in backup_fk] == ["NO ACTION"]
    assert preview_count == 1
