import json
from pathlib import Path

from fastapi.testclient import TestClient

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

    db_path = tmp_path / "db" / "legacy-action-safety.db"
    data_dir = tmp_path / "data"
    _load_legacy_fixture(
        db_path=db_path,
        source_root=source_root,
        approved_source=approved_source,
        approved_destination=approved_destination,
        executed_source=executed_source,
        executed_destination=executed_destination,
    )

    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(db_path))
    monkeypatch.setenv("PROOFFLOW_DATA_DIR", str(data_dir))

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

        undone_approved = client.post("/actions/legacy-approved-move/undo")
        assert undone_approved.status_code == 200
        assert undone_approved.json()["status"] == "undone"
        assert approved_source.read_text(encoding="utf-8") == "# Approved legacy note\n"
        assert not approved_destination.exists()


def _load_legacy_fixture(
    *,
    db_path: Path,
    source_root: Path,
    approved_source: Path,
    approved_destination: Path,
    executed_source: Path,
    executed_destination: Path,
) -> None:
    sql = FIXTURE_PATH.read_text(encoding="utf-8")
    replacements = {
        "__SOURCE_ROOT_JSON__": _json_path(source_root),
        "__APPROVED_SOURCE_JSON__": _json_path(approved_source),
        "__APPROVED_DEST_JSON__": _json_path(approved_destination),
        "__EXECUTED_SOURCE_JSON__": _json_path(executed_source),
        "__EXECUTED_DEST_JSON__": _json_path(executed_destination),
    }
    for token, value in replacements.items():
        sql = sql.replace(token, value)

    with connect(db_path) as connection:
        connection.executescript(sql)
        connection.commit()


def _json_path(path: Path) -> str:
    return json.dumps(str(path.resolve(strict=False)))
