from typing import Any

from proofflow.db import connect, new_uuid, utc_now_iso
from proofflow.models.schemas import (
    ArtifactCreate,
    ArtifactResponse,
    CaseArtifactLinkCreate,
    CaseArtifactLinkResponse,
)
from proofflow.services.errors import NotFoundError
from proofflow.services.json_utils import dumps_metadata, loads_metadata


def _artifact_from_row(row: Any) -> ArtifactResponse:
    return ArtifactResponse(
        id=row["id"],
        kind=row["artifact_type"],
        uri=row["uri"],
        name=row["name"],
        mime_type=row["mime_type"],
        sha256=row["sha256"],
        size_bytes=row["size_bytes"],
        metadata=loads_metadata(row["metadata_json"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _link_from_row(row: Any) -> CaseArtifactLinkResponse:
    return CaseArtifactLinkResponse(
        case_id=row["case_id"],
        artifact_id=row["artifact_id"],
        role=row["role"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def list_artifacts() -> list[ArtifactResponse]:
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT
                id, artifact_type, uri, name, mime_type, sha256, size_bytes,
                metadata_json, created_at, updated_at
            FROM artifacts
            ORDER BY created_at DESC, id ASC
            """
        ).fetchall()
    return [_artifact_from_row(row) for row in rows]


def create_artifact(payload: ArtifactCreate) -> ArtifactResponse:
    artifact_id = new_uuid()
    now = utc_now_iso()
    metadata_json = dumps_metadata(payload.metadata)

    with connect() as connection:
        connection.execute(
            """
            INSERT INTO artifacts (
                id, artifact_type, uri, name, mime_type, sha256, size_bytes,
                metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                artifact_id,
                payload.kind,
                payload.uri,
                payload.name,
                payload.mime_type,
                payload.sha256,
                payload.size_bytes,
                metadata_json,
                now,
                now,
            ),
        )
        connection.commit()

    return get_artifact(artifact_id)


def get_artifact(artifact_id: str) -> ArtifactResponse:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT
                id, artifact_type, uri, name, mime_type, sha256, size_bytes,
                metadata_json, created_at, updated_at
            FROM artifacts
            WHERE id = ?
            """,
            (artifact_id,),
        ).fetchone()

    if row is None:
        raise NotFoundError(f"artifact not found: {artifact_id}")
    return _artifact_from_row(row)


def link_artifact_to_case(
    case_id: str,
    artifact_id: str,
    payload: CaseArtifactLinkCreate,
) -> CaseArtifactLinkResponse:
    now = utc_now_iso()

    with connect() as connection:
        case_exists = connection.execute(
            "SELECT 1 FROM cases WHERE id = ?",
            (case_id,),
        ).fetchone()
        if case_exists is None:
            raise NotFoundError(f"case not found: {case_id}")

        artifact_exists = connection.execute(
            "SELECT 1 FROM artifacts WHERE id = ?",
            (artifact_id,),
        ).fetchone()
        if artifact_exists is None:
            raise NotFoundError(f"artifact not found: {artifact_id}")

        existing = connection.execute(
            """
            SELECT case_id, artifact_id, role, created_at, updated_at
            FROM case_artifacts
            WHERE case_id = ? AND artifact_id = ?
            """,
            (case_id, artifact_id),
        ).fetchone()

        if existing is not None and existing["role"] == payload.role:
            return _link_from_row(existing)

        if existing is None:
            connection.execute(
                """
                INSERT INTO case_artifacts (
                    case_id, artifact_id, role, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (case_id, artifact_id, payload.role, now, now),
            )
        else:
            connection.execute(
                """
                UPDATE case_artifacts
                SET role = ?, updated_at = ?
                WHERE case_id = ? AND artifact_id = ?
                """,
                (payload.role, now, case_id, artifact_id),
            )
        connection.commit()

        row = connection.execute(
            """
            SELECT case_id, artifact_id, role, created_at, updated_at
            FROM case_artifacts
            WHERE case_id = ? AND artifact_id = ?
            """,
            (case_id, artifact_id),
        ).fetchone()

    return _link_from_row(row)

