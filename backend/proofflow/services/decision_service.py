from typing import Any

from proofflow.db import connect, new_uuid, utc_now_iso
from proofflow.models.schemas import DecisionCreate, DecisionResponse, DecisionUpdate
from proofflow.services.errors import NotFoundError
from proofflow.services.json_utils import dumps_metadata


def list_case_decisions(case_id: str) -> list[DecisionResponse]:
    with connect() as connection:
        _ensure_case_exists(connection, case_id)
        rows = connection.execute(
            """
            SELECT id, case_id, title, status, rationale, result, created_at, updated_at
            FROM decisions
            WHERE case_id = ?
            ORDER BY created_at DESC, id ASC
            """,
            (case_id,),
        ).fetchall()
    return [_decision_from_row(row) for row in rows]


def create_decision(case_id: str, payload: DecisionCreate) -> DecisionResponse:
    now = utc_now_iso()
    decision_id = new_uuid()

    with connect() as connection:
        _ensure_case_exists(connection, case_id)
        connection.execute(
            """
            INSERT INTO decisions (
                id, case_id, title, status, rationale, result,
                metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id,
                case_id,
                payload.title,
                payload.status,
                payload.rationale,
                payload.result,
                dumps_metadata({}),
                now,
                now,
            ),
        )
        connection.commit()

    return get_decision(decision_id)


def get_decision(decision_id: str) -> DecisionResponse:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT id, case_id, title, status, rationale, result, created_at, updated_at
            FROM decisions
            WHERE id = ?
            """,
            (decision_id,),
        ).fetchone()

    if row is None:
        raise NotFoundError(f"decision not found: {decision_id}")
    return _decision_from_row(row)


def update_decision(decision_id: str, payload: DecisionUpdate) -> DecisionResponse:
    updates: list[str] = []
    values: list[Any] = []

    if "title" in payload.model_fields_set:
        updates.append("title = ?")
        values.append(payload.title)
    if "status" in payload.model_fields_set:
        updates.append("status = ?")
        values.append(payload.status)
    if "rationale" in payload.model_fields_set:
        updates.append("rationale = ?")
        values.append(payload.rationale)
    if "result" in payload.model_fields_set:
        updates.append("result = ?")
        values.append(payload.result)

    now = utc_now_iso()
    updates.append("updated_at = ?")
    values.append(now)
    values.append(decision_id)

    with connect() as connection:
        db_result = connection.execute(
            f"""
            UPDATE decisions
            SET {", ".join(updates)}
            WHERE id = ?
            """,
            values,
        )
        connection.commit()

    if db_result.rowcount == 0:
        raise NotFoundError(f"decision not found: {decision_id}")
    return get_decision(decision_id)


def _ensure_case_exists(connection: Any, case_id: str) -> None:
    row = connection.execute("SELECT 1 FROM cases WHERE id = ?", (case_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"case not found: {case_id}")


def _decision_from_row(row: Any) -> DecisionResponse:
    return DecisionResponse(
        id=row["id"],
        case_id=row["case_id"],
        title=row["title"],
        status=row["status"],
        rationale=row["rationale"],
        result=row["result"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
