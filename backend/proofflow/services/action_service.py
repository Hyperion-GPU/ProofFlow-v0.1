from pathlib import Path
from typing import Any

import json
import shutil

from proofflow.db import connect, new_uuid, utc_now_iso
from proofflow.models.schemas import ActionCreate, ActionResponse
from proofflow.services.errors import NotFoundError
from proofflow.services.json_utils import dumps_metadata, loads_metadata


class ActionError(ValueError):
    """Raised when an action cannot safely move through its lifecycle."""


def list_case_actions(case_id: str) -> list[ActionResponse]:
    with connect() as connection:
        _ensure_case_exists(connection, case_id)
        rows = connection.execute(
            """
            SELECT
                id, case_id, action_type, status, title, reason, preview_json,
                result_json, undo_json, metadata_json, created_at, updated_at
            FROM actions
            WHERE case_id = ?
            ORDER BY created_at DESC, id ASC
            """,
            (case_id,),
        ).fetchall()
    return [_action_from_row(row) for row in rows]


def create_action(payload: ActionCreate) -> ActionResponse:
    now = utc_now_iso()
    action_id = new_uuid()
    preview = payload.preview.model_dump() if payload.preview else {}

    with connect() as connection:
        _ensure_case_exists(connection, payload.case_id)
        connection.execute(
            """
            INSERT INTO actions (
                id, case_id, run_id, action_type, status, description, title, reason,
                preview_json, result_json, undo_json, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_id,
                payload.case_id,
                None,
                payload.kind,
                "previewed",
                payload.title,
                payload.title,
                payload.reason,
                dumps_metadata(preview),
                None,
                None,
                dumps_metadata(payload.metadata),
                now,
                now,
            ),
        )
        connection.commit()

    return get_action(action_id)


def get_action(action_id: str) -> ActionResponse:
    row = _get_action_row(action_id)
    return _action_from_row(row)


def approve_action(action_id: str) -> ActionResponse:
    row = _get_action_row(action_id)
    if row["status"] not in {"pending", "previewed"}:
        raise ActionError("only pending or previewed actions can be approved")

    now = utc_now_iso()
    with connect() as connection:
        connection.execute(
            "UPDATE actions SET status = ?, updated_at = ? WHERE id = ?",
            ("approved", now, action_id),
        )
        connection.commit()
    return get_action(action_id)


def execute_action(action_id: str) -> ActionResponse:
    row = _get_action_row(action_id)
    if row["status"] != "approved":
        raise ActionError("only approved actions can execute")

    kind = row["action_type"]
    now = utc_now_iso()

    if kind == "manual_check":
        result_json = dumps_metadata(
            {
                "executed_at": now,
                "message": "manual check recorded",
                "touched_files": False,
            }
        )
        with connect() as connection:
            connection.execute(
                """
                UPDATE actions
                SET status = ?, result_json = ?, updated_at = ?
                WHERE id = ?
                """,
                ("executed", result_json, now, action_id),
            )
            connection.commit()
        return get_action(action_id)

    if kind == "mkdir_dir":
        preview = _loads_required_json(row["preview_json"])
        dir_path = _validate_dir_preview(preview)
        created = _execute_mkdir_dir(dir_path)
        result = {
            "operation": "mkdir_dir",
            "dir_path": str(dir_path),
            "created": created,
            "already_exists": not created,
            "executed_at": now,
        }
        undo = {
            "operation": "remove_dir",
            "dir_path": str(dir_path),
            "created_by_action": created,
            "created_at": now,
        }
        with connect() as connection:
            connection.execute(
                """
                UPDATE actions
                SET status = ?, result_json = ?, undo_json = ?, updated_at = ?
                WHERE id = ?
                """,
                ("executed", dumps_metadata(result), dumps_metadata(undo), now, action_id),
            )
            connection.commit()
        return get_action(action_id)

    if kind not in {"move_file", "rename_file"}:
        raise ActionError(f"unsupported action kind: {kind}")

    _ensure_dependency_executed(row)
    preview = _loads_required_json(row["preview_json"])
    source_path, destination_path = _validate_file_preview(preview)
    if kind == "rename_file" and source_path.parent != destination_path.parent:
        raise ActionError("rename_file requires from_path and to_path in the same directory")

    _execute_file_move(source_path, destination_path)

    result = {
        "operation": kind,
        "from_path": str(source_path),
        "to_path": str(destination_path),
        "executed_at": now,
    }
    undo = {
        "operation": "restore_file",
        "from_path": str(destination_path),
        "to_path": str(source_path),
        "created_at": now,
    }

    with connect() as connection:
        connection.execute(
            """
            UPDATE actions
            SET status = ?, result_json = ?, undo_json = ?, updated_at = ?
            WHERE id = ?
            """,
            ("executed", dumps_metadata(result), dumps_metadata(undo), now, action_id),
        )
        connection.commit()
    return get_action(action_id)


def undo_action(action_id: str) -> ActionResponse:
    row = _get_action_row(action_id)
    if row["status"] != "executed":
        raise ActionError("only executed actions can be undone")
    if row["action_type"] == "manual_check":
        raise ActionError("manual_check actions do not have file undo operations")

    undo = _loads_required_json(row["undo_json"])
    if row["action_type"] == "mkdir_dir":
        _undo_mkdir_dir(undo)
        now = utc_now_iso()
        undo["undone_at"] = now
        with connect() as connection:
            connection.execute(
                """
                UPDATE actions
                SET status = ?, undo_json = ?, updated_at = ?
                WHERE id = ?
                """,
                ("undone", dumps_metadata(undo), now, action_id),
            )
            connection.commit()
        return get_action(action_id)

    source_path = _resolve_user_path(undo.get("from_path"))
    destination_path = _resolve_user_path(undo.get("to_path"))

    _undo_file_move(source_path, destination_path)

    now = utc_now_iso()
    undo["undone_at"] = now
    with connect() as connection:
        connection.execute(
            """
            UPDATE actions
            SET status = ?, undo_json = ?, updated_at = ?
            WHERE id = ?
            """,
            ("undone", dumps_metadata(undo), now, action_id),
        )
        connection.commit()
    return get_action(action_id)


def reject_action(action_id: str) -> ActionResponse:
    row = _get_action_row(action_id)
    if row["status"] not in {"pending", "previewed", "approved"}:
        raise ActionError("only pending, previewed, or approved actions can be rejected")

    now = utc_now_iso()
    result = {"rejected_at": now}
    with connect() as connection:
        connection.execute(
            """
            UPDATE actions
            SET status = ?, result_json = ?, updated_at = ?
            WHERE id = ?
            """,
            ("rejected", dumps_metadata(result), now, action_id),
        )
        connection.commit()
    return get_action(action_id)


def _ensure_case_exists(connection: Any, case_id: str) -> None:
    row = connection.execute("SELECT 1 FROM cases WHERE id = ?", (case_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"case not found: {case_id}")


def _get_action_row(action_id: str):
    with connect() as connection:
        row = connection.execute(
            """
            SELECT
                id, case_id, action_type, status, title, reason, preview_json,
                result_json, undo_json, metadata_json, created_at, updated_at
            FROM actions
            WHERE id = ?
            """,
            (action_id,),
        ).fetchone()
    if row is None:
        raise NotFoundError(f"action not found: {action_id}")
    return row


def _action_from_row(row: Any) -> ActionResponse:
    return ActionResponse(
        id=row["id"],
        case_id=row["case_id"],
        kind=row["action_type"],
        status=row["status"],
        title=row["title"],
        reason=row["reason"],
        preview=loads_metadata(row["preview_json"]),
        result=_loads_optional_json(row["result_json"]),
        undo=_loads_optional_json(row["undo_json"]),
        metadata=loads_metadata(row["metadata_json"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _loads_optional_json(raw_json: str | None) -> dict[str, Any] | None:
    if not raw_json:
        return None
    try:
        decoded = json.loads(raw_json)
    except json.JSONDecodeError:
        return None
    if isinstance(decoded, dict):
        return decoded
    return None


def _loads_required_json(raw_json: str | None) -> dict[str, Any]:
    decoded = _loads_optional_json(raw_json)
    if decoded is None:
        raise ActionError("action is missing required JSON state")
    return decoded


def _validate_file_preview(preview: dict[str, Any]) -> tuple[Path, Path]:
    source_path = _resolve_user_path(preview.get("from_path"))
    destination_path = _resolve_user_path(preview.get("to_path"))

    if source_path.is_symlink():
        raise ActionError("source file cannot be a symlink")
    if not source_path.exists():
        raise ActionError("source file does not exist")
    if not source_path.is_file():
        raise ActionError("source path is not a regular file")
    if destination_path.exists():
        raise ActionError("destination already exists")
    if not destination_path.parent.exists() or not destination_path.parent.is_dir():
        raise ActionError("destination parent directory does not exist")

    return source_path, destination_path


def _validate_dir_preview(preview: dict[str, Any]) -> Path:
    dir_path = _resolve_user_path(preview.get("dir_path"))
    if dir_path.exists():
        if dir_path.is_symlink():
            raise ActionError("directory path cannot be a symlink")
        if not dir_path.is_dir():
            raise ActionError("directory path exists but is not a directory")
    return dir_path


def _ensure_dependency_executed(row: Any) -> None:
    metadata = loads_metadata(row["metadata_json"])
    dependency_id = metadata.get("depends_on_action_id")
    if not isinstance(dependency_id, str) or not dependency_id:
        return

    with connect() as connection:
        dependency = connection.execute(
            """
            SELECT case_id, status
            FROM actions
            WHERE id = ?
            """,
            (dependency_id,),
        ).fetchone()
    if dependency is None or dependency["case_id"] != row["case_id"]:
        raise ActionError("dependent action was not found in this case")
    if dependency["status"] != "executed":
        raise ActionError("dependent action must be executed first")


def _execute_mkdir_dir(dir_path: Path) -> bool:
    if dir_path.exists():
        if dir_path.is_symlink():
            raise ActionError("directory path cannot be a symlink")
        if not dir_path.is_dir():
            raise ActionError("directory path exists but is not a directory")
        return False
    try:
        dir_path.mkdir(parents=True, exist_ok=False)
    except OSError as error:
        raise ActionError(f"directory create failed: {error}") from error
    return True


def _undo_mkdir_dir(undo: dict[str, Any]) -> None:
    dir_path = _resolve_user_path(undo.get("dir_path"))
    if undo.get("created_by_action") is not True:
        undo["removed"] = False
        undo["skipped_reason"] = "directory_not_created_by_action"
        return
    if dir_path.is_symlink():
        raise ActionError("undo directory cannot be a symlink")
    if not dir_path.exists():
        raise ActionError("directory created by action no longer exists")
    if not dir_path.is_dir():
        raise ActionError("undo path is not a directory")
    try:
        dir_path.rmdir()
    except OSError as error:
        raise ActionError(f"directory undo failed: {error}") from error
    undo["removed"] = True


def _execute_file_move(source_path: Path, destination_path: Path) -> None:
    try:
        shutil.move(str(source_path), str(destination_path))
    except OSError as error:
        raise ActionError(f"file move failed: {error}") from error


def _undo_file_move(source_path: Path, destination_path: Path) -> None:
    if source_path.is_symlink():
        raise ActionError("undo source cannot be a symlink")
    if not source_path.exists():
        raise ActionError("original destination no longer exists")
    if not source_path.is_file():
        raise ActionError("undo source is not a regular file")
    if destination_path.exists():
        raise ActionError("original source path is occupied")
    if not destination_path.parent.exists() or not destination_path.parent.is_dir():
        raise ActionError("original source parent directory does not exist")
    try:
        shutil.move(str(source_path), str(destination_path))
    except OSError as error:
        raise ActionError(f"file undo failed: {error}") from error


def _resolve_user_path(value: Any) -> Path:
    if not isinstance(value, str) or not value:
        raise ActionError("action path must be a non-empty string")
    return Path(value).expanduser()
