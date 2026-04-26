from typing import Any

from proofflow.db import connect, new_uuid, utc_now_iso
from proofflow.models.schemas import CaseCreate, CaseDetailResponse, CaseResponse, CaseUpdate
from proofflow.services.errors import NotFoundError
from proofflow.services.json_utils import dumps_metadata, loads_metadata


def _case_from_row(row: Any) -> CaseResponse:
    return CaseResponse(
        id=row["id"],
        title=row["title"],
        kind=row["case_type"],
        status=row["status"],
        summary=row["summary"],
        metadata=loads_metadata(row["metadata_json"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _case_detail_from_row(row: Any, decision_count: int) -> CaseDetailResponse:
    case = _case_from_row(row)
    return CaseDetailResponse(
        **case.model_dump(),
        decision_count=decision_count,
    )


def list_cases() -> list[CaseResponse]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT id, title, case_type, status, summary, metadata_json, created_at, updated_at
            FROM cases
            ORDER BY created_at DESC, id ASC
            """
        ).fetchall()
    return [_case_from_row(row) for row in rows]


def create_case(payload: CaseCreate) -> CaseResponse:
    case_id = new_uuid()
    now = utc_now_iso()
    metadata_json = dumps_metadata(payload.metadata)

    with connect() as connection:
        connection.execute(
            """
            INSERT INTO cases (
                id, title, case_type, status, summary, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                payload.title,
                payload.kind,
                payload.status,
                payload.summary,
                metadata_json,
                now,
                now,
            ),
        )
        connection.commit()

    return get_case(case_id)


def get_case(case_id: str) -> CaseResponse:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT id, title, case_type, status, summary, metadata_json, created_at, updated_at
            FROM cases
            WHERE id = ?
            """,
            (case_id,),
        ).fetchone()

    if row is None:
        raise NotFoundError(f"case not found: {case_id}")
    return _case_from_row(row)


def get_case_detail(case_id: str) -> CaseDetailResponse:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT id, title, case_type, status, summary, metadata_json, created_at, updated_at
            FROM cases
            WHERE id = ?
            """,
            (case_id,),
        ).fetchone()
        if row is None:
            raise NotFoundError(f"case not found: {case_id}")

        decision_count = connection.execute(
            "SELECT COUNT(*) FROM decisions WHERE case_id = ?",
            (case_id,),
        ).fetchone()[0]

    return _case_detail_from_row(row, decision_count)


def update_case(case_id: str, payload: CaseUpdate) -> CaseResponse:
    updates: list[str] = []
    values: list[Any] = []

    if "title" in payload.model_fields_set:
        updates.append("title = ?")
        values.append(payload.title)
    if "status" in payload.model_fields_set:
        updates.append("status = ?")
        values.append(payload.status)
    if "summary" in payload.model_fields_set:
        updates.append("summary = ?")
        values.append(payload.summary)
    if "metadata" in payload.model_fields_set:
        updates.append("metadata_json = ?")
        values.append(dumps_metadata(payload.metadata or {}))

    now = utc_now_iso()
    updates.append("updated_at = ?")
    values.append(now)
    values.append(case_id)

    with connect() as connection:
        result = connection.execute(
            f"""
            UPDATE cases
            SET {", ".join(updates)}
            WHERE id = ?
            """,
            values,
        )
        connection.commit()

    if result.rowcount == 0:
        raise NotFoundError(f"case not found: {case_id}")
    return get_case(case_id)
