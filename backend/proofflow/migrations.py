import hashlib
from pathlib import Path
from typing import Any

from proofflow.db import connect, resolve_db_path
from proofflow.services.action_safety import (
    ActionSafetyError,
    LOCALPROOF_METADATA_SOURCE,
    LOCALPROOF_SCOPE_KIND,
    validate_filesystem_action_scope,
)
from proofflow.services.json_utils import dumps_metadata, loads_metadata

SCHEMA_PATH = Path(__file__).resolve().parent / "storage" / "schema.sql"
FILESYSTEM_ACTION_KINDS = {"move_file", "rename_file", "mkdir_dir"}
FILE_MOVE_ACTION_KINDS = {"move_file", "rename_file"}


def init_db(db_path: str | Path | None = None) -> Path:
    resolved_path = resolve_db_path(db_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with connect(resolved_path) as connection:
        connection.executescript(schema_sql)
        _ensure_action_columns(connection)
        _ensure_decision_table(connection)
        _ensure_action_safety_metadata(connection)
        connection.commit()

    return resolved_path


def _ensure_action_columns(connection) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(actions)").fetchall()
    }
    required_columns = {
        "title": "TEXT NOT NULL DEFAULT ''",
        "reason": "TEXT NOT NULL DEFAULT ''",
        "preview_json": "TEXT NOT NULL DEFAULT '{}'",
        "result_json": "TEXT",
        "undo_json": "TEXT",
    }

    for column_name, column_definition in required_columns.items():
        if column_name not in existing_columns:
            connection.execute(
                f"ALTER TABLE actions ADD COLUMN {column_name} {column_definition}"
            )


def _ensure_decision_table(connection) -> None:
    columns = {
        row["name"]: row
        for row in connection.execute("PRAGMA table_info(decisions)").fetchall()
    }
    required_columns = {
        "id",
        "case_id",
        "title",
        "status",
        "rationale",
        "result",
        "metadata_json",
        "created_at",
        "updated_at",
    }

    if required_columns.issubset(columns) and "action_id" not in columns and "decision" not in columns:
        return

    _rebuild_decisions_table(connection, columns)


def _rebuild_decisions_table(connection, legacy_columns) -> None:
    connection.execute("DROP TABLE IF EXISTS decisions_legacy_migration")
    connection.execute("ALTER TABLE decisions RENAME TO decisions_legacy_migration")
    _create_decisions_table(connection)
    _copy_legacy_decisions(connection, legacy_columns)
    connection.execute("DROP TABLE decisions_legacy_migration")


def _ensure_action_safety_metadata(connection) -> None:
    rows = connection.execute(
        """
        SELECT
            actions.id,
            actions.action_type,
            actions.status,
            actions.preview_json,
            actions.result_json,
            actions.undo_json,
            actions.metadata_json,
            cases.metadata_json AS case_metadata_json
        FROM actions
        LEFT JOIN cases ON cases.id = actions.case_id
        WHERE actions.action_type IN ('move_file', 'rename_file', 'mkdir_dir')
        """
    ).fetchall()

    for row in rows:
        kind = row["action_type"]
        preview = loads_metadata(row["preview_json"])
        metadata = loads_metadata(row["metadata_json"])
        case_metadata = loads_metadata(row["case_metadata_json"])

        updated_metadata = _legacy_action_scope_metadata(kind, preview, metadata, case_metadata)
        updated_result = _loads_optional_metadata(row["result_json"])
        updated_undo = _loads_optional_metadata(row["undo_json"])

        if row["status"] == "executed" and kind in FILE_MOVE_ACTION_KINDS and updated_undo is not None:
            updated_undo, updated_result = _ensure_legacy_undo_hash_guard(
                updated_undo,
                updated_result,
            )

        connection.execute(
            """
            UPDATE actions
            SET metadata_json = ?, result_json = ?, undo_json = ?
            WHERE id = ?
            """,
            (
                dumps_metadata(updated_metadata),
                dumps_metadata(updated_result) if updated_result is not None else row["result_json"],
                dumps_metadata(updated_undo) if updated_undo is not None else row["undo_json"],
                row["id"],
            ),
        )


def _legacy_action_scope_metadata(
    kind: str,
    preview: dict[str, Any],
    metadata: dict[str, Any],
    case_metadata: dict[str, Any],
) -> dict[str, Any]:
    if kind not in FILESYSTEM_ACTION_KINDS or _has_allowed_roots(metadata):
        return metadata

    if metadata.get("source") == LOCALPROOF_METADATA_SOURCE:
        scoped_metadata = _legacy_localproof_scope_metadata(kind, preview, metadata, case_metadata)
    else:
        scoped_metadata = _legacy_generic_scope_metadata(kind, preview, metadata)

    try:
        return validate_filesystem_action_scope(kind, preview, scoped_metadata)
    except ActionSafetyError:
        return metadata


def _legacy_localproof_scope_metadata(
    kind: str,
    preview: dict[str, Any],
    metadata: dict[str, Any],
    case_metadata: dict[str, Any],
) -> dict[str, Any]:
    source_root = _path_from_metadata(case_metadata, "folder_path")
    target_root = _infer_localproof_target_root(kind, preview, metadata)
    if source_root is None or target_root is None:
        return metadata

    return {
        **metadata,
        "scope_kind": LOCALPROOF_SCOPE_KIND,
        "source_root": str(source_root),
        "target_root": str(target_root),
        "allowed_roots": [str(source_root), str(target_root)],
        "scope_migrated_from": "legacy_action_safety_v0",
    }


def _legacy_generic_scope_metadata(
    kind: str,
    preview: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    allowed_roots = _infer_generic_allowed_roots(kind, preview)
    if not allowed_roots:
        return metadata
    return {
        **metadata,
        "scope_kind": metadata.get("scope_kind", "legacy_filesystem_action"),
        "allowed_roots": [str(root) for root in allowed_roots],
        "scope_migrated_from": "legacy_action_safety_v0",
    }


def _has_allowed_roots(metadata: dict[str, Any]) -> bool:
    roots = metadata.get("allowed_roots")
    return isinstance(roots, list) and bool(roots)


def _path_from_metadata(metadata: dict[str, Any], key: str) -> Path | None:
    raw_path = metadata.get(key)
    if not isinstance(raw_path, str) or not raw_path:
        return None
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        return None
    return path.resolve(strict=False)


def _infer_localproof_target_root(
    kind: str,
    preview: dict[str, Any],
    metadata: dict[str, Any],
) -> Path | None:
    category = metadata.get("category")
    if kind == "mkdir_dir":
        dir_path = _preview_path(preview, "dir_path")
        if dir_path is None:
            return None
        if isinstance(category, str) and category and dir_path.name == category:
            return dir_path.parent.resolve(strict=False)
        return dir_path.resolve(strict=False)

    destination = _preview_path(preview, "to_path")
    if destination is None:
        return None
    destination_dir = destination.parent
    if isinstance(category, str) and category and destination_dir.name == category:
        return destination_dir.parent.resolve(strict=False)
    return destination_dir.resolve(strict=False)


def _infer_generic_allowed_roots(kind: str, preview: dict[str, Any]) -> list[Path]:
    roots: list[Path] = []
    if kind in FILE_MOVE_ACTION_KINDS:
        for key in ("from_path", "to_path"):
            path = _preview_path(preview, key)
            if path is not None:
                roots.append(path.parent.resolve(strict=False))
    elif kind == "mkdir_dir":
        path = _preview_path(preview, "dir_path")
        if path is not None:
            roots.append(path.parent.resolve(strict=False))
    return _dedupe_paths(roots)


def _preview_path(preview: dict[str, Any], key: str) -> Path | None:
    raw_path = preview.get(key)
    if not isinstance(raw_path, str) or not raw_path:
        return None
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        return None
    return path.resolve(strict=False)


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    deduped: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path).casefold()
        if key not in seen:
            seen.add(key)
            deduped.append(path)
    return deduped


def _loads_optional_metadata(raw_json: str | None) -> dict[str, Any] | None:
    if not raw_json:
        return None
    return loads_metadata(raw_json)


def _ensure_legacy_undo_hash_guard(
    undo: dict[str, Any],
    result: dict[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if isinstance(undo.get("from_sha256"), str) and undo["from_sha256"]:
        return undo, result

    source_path = _path_from_metadata(undo, "from_path")
    if source_path is None or source_path.is_symlink() or not source_path.is_file():
        return undo, result

    sha256 = _sha256_file(source_path)
    size_bytes = source_path.stat().st_size
    undo = {
        **undo,
        "from_sha256": sha256,
        "from_size_bytes": size_bytes,
        "hash_guard_migrated_from": "legacy_action_safety_v0",
    }
    if result is not None:
        result = {
            **result,
            "sha256": result.get("sha256", sha256),
            "size_bytes": result.get("size_bytes", size_bytes),
            "hash_guard_migrated_from": "legacy_action_safety_v0",
        }
    return undo, result


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _create_decisions_table(connection) -> None:
    connection.execute(
        """
        CREATE TABLE decisions (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            rationale TEXT NOT NULL,
            result TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE
        )
        """
    )


def _copy_legacy_decisions(connection, legacy_columns) -> None:
    now = "1970-01-01T00:00:00Z"
    title_source = _legacy_column_source(legacy_columns, "title", "decision", "''")
    result_source = _legacy_column_source(legacy_columns, "result", "decision", "title", "''")
    rationale_source = _legacy_column_source(legacy_columns, "rationale", "''")
    metadata_source = _legacy_column_source(legacy_columns, "metadata_json", "'{}'")
    created_source = _legacy_column_source(legacy_columns, "created_at", f"'{now}'")
    updated_source = _legacy_column_source(legacy_columns, "updated_at", f"'{now}'")

    if "status" in legacy_columns:
        status_source = (
            "CASE WHEN status IN ('proposed','accepted','rejected','superseded') "
            "THEN status ELSE 'accepted' END"
        )
    else:
        status_source = "'accepted'"

    connection.execute(
        f"""
        INSERT INTO decisions (
            id, case_id, title, status, rationale, result,
            metadata_json, created_at, updated_at
        )
        SELECT
            id,
            case_id,
            COALESCE(NULLIF({title_source}, ''), 'Untitled decision'),
            {status_source},
            COALESCE({rationale_source}, ''),
            COALESCE(NULLIF({result_source}, ''), COALESCE(NULLIF({title_source}, ''), 'Migrated decision')),
            COALESCE({metadata_source}, '{{}}'),
            COALESCE({created_source}, '{now}'),
            COALESCE({updated_source}, '{now}')
        FROM decisions_legacy_migration
        """
    )


def _legacy_column_source(legacy_columns, *candidates: str) -> str:
    for candidate in candidates:
        if candidate in legacy_columns:
            return candidate
    return candidates[-1]
