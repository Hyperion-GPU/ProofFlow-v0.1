import json
from pathlib import Path

from fastapi.testclient import TestClient

from proofflow import migrations
from proofflow.db import connect
from proofflow.main import app


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "legacy_action_safety_v0.sql"


def test_legacy_filesystem_actions_continue_after_action_safety_upgrade(
    monkeypatch,
    tmp_path: Path,
):
    source_root = tmp_path / "legacy-scan"
    target_root = tmp_path / "legacy-sorted"
    target_notes = target_root / "Notes"
    source_root.mkdir()
    target_notes.mkdir(parents=True)

    approved_source = source_root / "approved-note.md"
    approved_destination = target_notes / "approved-note.md"
    approved_source.write_text("# Approved legacy note\n", encoding="utf-8")

    executed_source = source_root / "executed-note.md"
    executed_destination = target_notes / "executed-note.md"
    executed_destination.write_text("# Executed legacy note\n", encoding="utf-8")

    relative_approved_source = source_root / "relative-approved-note.md"
    relative_approved_destination = target_notes / "relative-approved-note.md"
    relative_approved_source.write_text("# Relative approved legacy note\n", encoding="utf-8")

    relative_executed_source = source_root / "relative-executed-note.md"
    relative_executed_destination = target_notes / "relative-executed-note.md"
    relative_executed_destination.write_text(
        "# Relative executed legacy note\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "db" / "legacy-action-safety.db"
    data_dir = tmp_path / "data"
    _load_legacy_fixture(
        db_path=db_path,
        source_root=source_root,
        approved_source=approved_source,
        approved_destination=approved_destination,
        executed_source=executed_source,
        executed_destination=executed_destination,
        relative_approved_source=relative_approved_source,
        relative_approved_destination=relative_approved_destination,
        relative_executed_source=relative_executed_source,
        relative_executed_destination=relative_executed_destination,
    )

    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(db_path))
    monkeypatch.setenv("PROOFFLOW_DATA_DIR", str(data_dir))
    monkeypatch.chdir(tmp_path)

    with TestClient(app) as client:
        list_response = client.get("/cases/case-legacy-actions/actions")
        assert list_response.status_code == 200
        actions = {action["id"]: action for action in list_response.json()}

        approved_action = actions["legacy-approved-move"]
        assert approved_action["status"] == "approved"
        assert approved_action["metadata"]["scope_kind"] == "localproof_file_cleanup"
        assert approved_action["metadata"]["source_root"] == str(source_root.resolve())
        assert approved_action["metadata"]["target_root"] == str(target_root.resolve())
        assert set(approved_action["metadata"]["allowed_roots"]) == {
            str(source_root.resolve()),
            str(target_root.resolve()),
        }

        executed_action = actions["legacy-executed-move"]
        assert executed_action["status"] == "executed"
        assert executed_action["undo"]["from_sha256"]
        assert executed_action["undo"]["hash_guard_migrated_from"] == "legacy_action_safety_v0"

        relative_approved_action = actions["legacy-relative-approved-move"]
        assert relative_approved_action["status"] == "approved"
        assert relative_approved_action["preview"]["from_path"] == str(
            relative_approved_source.resolve()
        )
        assert relative_approved_action["preview"]["to_path"] == str(
            relative_approved_destination.resolve()
        )
        assert relative_approved_action["metadata"]["path_migrated_from"] == (
            "legacy_relative_action_paths"
        )
        assert relative_approved_action["metadata"]["legacy_relative_path_base"] == str(
            tmp_path.resolve()
        )
        assert set(relative_approved_action["metadata"]["allowed_roots"]) == {
            str(source_root.resolve()),
            str(target_root.resolve()),
        }

        relative_executed_action = actions["legacy-relative-executed-move"]
        assert relative_executed_action["status"] == "executed"
        assert relative_executed_action["undo"]["from_path"] == str(
            relative_executed_destination.resolve()
        )
        assert relative_executed_action["undo"]["to_path"] == str(
            relative_executed_source.resolve()
        )
        assert relative_executed_action["undo"]["from_sha256"]
        assert relative_executed_action["metadata"]["path_migrated_from"] == (
            "legacy_relative_action_paths"
        )

        executed = client.post("/actions/legacy-approved-move/execute")
        assert executed.status_code == 200
        assert executed.json()["status"] == "executed"
        assert not approved_source.exists()
        assert approved_destination.read_text(encoding="utf-8") == "# Approved legacy note\n"

        undone_legacy = client.post("/actions/legacy-executed-move/undo")
        assert undone_legacy.status_code == 200
        assert undone_legacy.json()["status"] == "undone"
        assert executed_source.read_text(encoding="utf-8") == "# Executed legacy note\n"
        assert not executed_destination.exists()

        executed_relative = client.post("/actions/legacy-relative-approved-move/execute")
        assert executed_relative.status_code == 200
        assert executed_relative.json()["status"] == "executed"
        assert not relative_approved_source.exists()
        assert relative_approved_destination.read_text(encoding="utf-8") == (
            "# Relative approved legacy note\n"
        )

        undone_relative_legacy = client.post("/actions/legacy-relative-executed-move/undo")
        assert undone_relative_legacy.status_code == 200
        assert undone_relative_legacy.json()["status"] == "undone"
        assert relative_executed_source.read_text(encoding="utf-8") == (
            "# Relative executed legacy note\n"
        )
        assert not relative_executed_destination.exists()

        undone_approved = client.post("/actions/legacy-approved-move/undo")
        assert undone_approved.status_code == 200
        assert undone_approved.json()["status"] == "undone"
        assert approved_source.read_text(encoding="utf-8") == "# Approved legacy note\n"
        assert not approved_destination.exists()

        undone_relative_approved = client.post("/actions/legacy-relative-approved-move/undo")
        assert undone_relative_approved.status_code == 200
        assert undone_relative_approved.json()["status"] == "undone"
        assert relative_approved_source.read_text(encoding="utf-8") == (
            "# Relative approved legacy note\n"
        )
        assert not relative_approved_destination.exists()


def test_legacy_hash_guard_migration_records_read_failure(
    monkeypatch,
    tmp_path: Path,
):
    source_root = tmp_path / "legacy-scan"
    target_root = tmp_path / "legacy-sorted"
    target_notes = target_root / "Notes"
    source_root.mkdir()
    target_notes.mkdir(parents=True)

    approved_source = source_root / "approved-note.md"
    approved_destination = target_notes / "approved-note.md"
    approved_source.write_text("# Approved legacy note\n", encoding="utf-8")

    executed_source = source_root / "executed-note.md"
    executed_destination = target_notes / "executed-note.md"
    executed_destination.write_text("# Executed legacy note\n", encoding="utf-8")

    relative_approved_source = source_root / "relative-approved-note.md"
    relative_approved_destination = target_notes / "relative-approved-note.md"
    relative_approved_source.write_text("# Relative approved legacy note\n", encoding="utf-8")

    relative_executed_source = source_root / "relative-executed-note.md"
    relative_executed_destination = target_notes / "relative-executed-note.md"
    relative_executed_destination.write_text(
        "# Relative executed legacy note\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "db" / "legacy-action-safety.db"
    _load_legacy_fixture(
        db_path=db_path,
        source_root=source_root,
        approved_source=approved_source,
        approved_destination=approved_destination,
        executed_source=executed_source,
        executed_destination=executed_destination,
        relative_approved_source=relative_approved_source,
        relative_approved_destination=relative_approved_destination,
        relative_executed_source=relative_executed_source,
        relative_executed_destination=relative_executed_destination,
    )

    def failing_sha256(path: Path) -> str:
        if path == executed_destination.resolve():
            raise OSError("simulated migration hash read failure")
        return "0" * 64

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(migrations, "_sha256_file", failing_sha256)

    migrations.init_db(db_path)

    with connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT status, result_json, undo_json
            FROM actions
            WHERE id = ?
            """,
            ("legacy-executed-move",),
        ).fetchone()

    assert row is not None
    assert row["status"] == "executed"
    result = json.loads(row["result_json"])
    undo = json.loads(row["undo_json"])
    assert "sha256" not in result
    assert "from_sha256" not in undo
    assert undo["hash_guard_migration_failed"] is True
    assert result["hash_guard_migration_failed"] is True
    assert "simulated migration hash read failure" in undo["hash_guard_migration_error"]


def _load_legacy_fixture(
    *,
    db_path: Path,
    source_root: Path,
    approved_source: Path,
    approved_destination: Path,
    executed_source: Path,
    executed_destination: Path,
    relative_approved_source: Path,
    relative_approved_destination: Path,
    relative_executed_source: Path,
    relative_executed_destination: Path,
) -> None:
    sql = FIXTURE_PATH.read_text(encoding="utf-8")
    legacy_base_dir = source_root.parent
    replacements = {
        "__SOURCE_ROOT_JSON__": _json_path(source_root),
        "__APPROVED_SOURCE_JSON__": _json_path(approved_source),
        "__APPROVED_DEST_JSON__": _json_path(approved_destination),
        "__EXECUTED_SOURCE_JSON__": _json_path(executed_source),
        "__EXECUTED_DEST_JSON__": _json_path(executed_destination),
        "__RELATIVE_APPROVED_SOURCE_JSON__": _json_relative_path(
            relative_approved_source,
            legacy_base_dir,
        ),
        "__RELATIVE_APPROVED_DEST_JSON__": _json_relative_path(
            relative_approved_destination,
            legacy_base_dir,
        ),
        "__RELATIVE_EXECUTED_SOURCE_JSON__": _json_relative_path(
            relative_executed_source,
            legacy_base_dir,
        ),
        "__RELATIVE_EXECUTED_DEST_JSON__": _json_relative_path(
            relative_executed_destination,
            legacy_base_dir,
        ),
    }
    for token, value in replacements.items():
        sql = sql.replace(token, value)

    with connect(db_path) as connection:
        connection.executescript(sql)
        connection.commit()


def _json_path(path: Path) -> str:
    return json.dumps(str(path.resolve(strict=False)))


def _json_relative_path(path: Path, base_dir: Path) -> str:
    return json.dumps(path.relative_to(base_dir).as_posix())
