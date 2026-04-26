from pathlib import Path

from proofflow.db import connect, resolve_db_path

SCHEMA_PATH = Path(__file__).resolve().parent / "storage" / "schema.sql"


def init_db(db_path: str | Path | None = None) -> Path:
    resolved_path = resolve_db_path(db_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with connect(resolved_path) as connection:
        connection.executescript(schema_sql)
        _ensure_action_columns(connection)
        _ensure_decision_table(connection)
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
