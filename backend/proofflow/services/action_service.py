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

    if kind not in {"move_file", "rename_file"}:
        raise ActionError(f"unsupported action kind: {kind}")

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
        raise ActionError("file action requires from_path and to_path")
    return Path(value).expanduser()
