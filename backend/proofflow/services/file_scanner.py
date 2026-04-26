from dataclasses import dataclass
from pathlib import Path
from typing import Any

import hashlib
import mimetypes

from proofflow.db import connect, new_uuid, utc_now_iso
from proofflow.models.schemas import (
    LocalProofScanRequest,
    LocalProofScanSummary,
    LocalProofSkippedItem,
)
from proofflow.services.json_utils import dumps_metadata
from proofflow.services.text_extractor import (
    MAX_TEXT_EXTRACTION_BYTES,
    extract_text_chunks,
    is_text_extractable,
)

TEXT_EXTENSIONS = {".txt", ".md", ".csv"}
CODE_EXTENSIONS = {".py", ".json", ".yaml", ".yml"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class ScanPathError(ValueError):
    """Raised when the requested scan folder is invalid."""


@dataclass(frozen=True)
class FileMetadata:
    path: Path
    uri: str
    name: str
    relative_path: str
    sha256: str
    size_bytes: int
    mime_type: str | None
    artifact_kind: str
    extension: str


@dataclass(frozen=True)
class ArtifactWriteResult:
    artifact_id: str
    created: bool


def scan_folder(request: LocalProofScanRequest) -> LocalProofScanSummary:
    folder = Path(request.folder_path).expanduser()
    if not folder.exists() or not folder.is_dir():
        raise ScanPathError(f"folder does not exist or is not a directory: {request.folder_path}")

    root = folder.resolve()
    case_id = _create_file_cleanup_case(root, request)

    files_seen = 0
    artifacts_created = 0
    artifacts_updated = 0
    text_chunks_created = 0
    skipped_items: list[LocalProofSkippedItem] = []

    for path in _walk_regular_files(root, request.recursive, skipped_items):
        if files_seen >= request.max_files:
            break

        metadata = _collect_file_metadata(root, path)
        files_seen += 1

        with connect() as connection:
            artifact_result = _upsert_artifact(connection, metadata)
            _link_artifact(connection, case_id, artifact_result.artifact_id)
            if is_text_extractable(path):
                if metadata.size_bytes > MAX_TEXT_EXTRACTION_BYTES:
                    skipped_items.append(
                        LocalProofSkippedItem(
                            path=str(path),
                            reason="text_too_large",
                            indexed=True,
                        )
                    )
                else:
                    text_chunks_created += _replace_text_chunks(
                        connection,
                        artifact_result.artifact_id,
                        path,
                    )
            connection.commit()

        if artifact_result.created:
            artifacts_created += 1
        else:
            artifacts_updated += 1

    return LocalProofScanSummary(
        case_id=case_id,
        files_seen=files_seen,
        artifacts_created=artifacts_created,
        artifacts_updated=artifacts_updated,
        text_chunks_created=text_chunks_created,
        skipped=len(skipped_items),
        skipped_items=skipped_items,
    )


def _create_file_cleanup_case(root: Path, request: LocalProofScanRequest) -> str:
    now = utc_now_iso()
    case_id = new_uuid()
    metadata = {
        "folder_path": str(root),
        "recursive": request.recursive,
        "max_files": request.max_files,
        "source": "localproof_scan",
    }
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
                f"File cleanup scan: {root.name}",
                "file_cleanup",
                "open",
                f"LocalProof scan for {root}",
                dumps_metadata(metadata),
                now,
                now,
            ),
        )
        connection.commit()
    return case_id


def _walk_regular_files(
    root: Path,
    recursive: bool,
    skipped_items: list[LocalProofSkippedItem],
) -> list[Path]:
    files: list[Path] = []

    def visit(directory: Path) -> None:
        try:
            children = sorted(directory.iterdir(), key=lambda item: str(item).lower())
        except OSError as error:
            skipped_items.append(
                LocalProofSkippedItem(path=str(directory), reason=f"read_error:{error.__class__.__name__}", indexed=False)
            )
            return

        for child in children:
            if child.is_symlink():
                skipped_items.append(
                    LocalProofSkippedItem(path=str(child), reason="symlink", indexed=False)
                )
                continue
            if child.is_file():
                files.append(child)
                continue
            if recursive and child.is_dir():
                visit(child)

    visit(root)
    return files


def _collect_file_metadata(root: Path, path: Path) -> FileMetadata:
    resolved = path.resolve()
    stat = resolved.stat()
    extension = resolved.suffix.lower()
    return FileMetadata(
        path=resolved,
        uri=resolved.as_uri(),
        name=resolved.name,
        relative_path=resolved.relative_to(root).as_posix(),
        sha256=_sha256_file(resolved),
        size_bytes=stat.st_size,
        mime_type=mimetypes.guess_type(resolved.name)[0],
        artifact_kind=_artifact_kind_for_extension(extension),
        extension=extension,
    )


def _artifact_kind_for_extension(extension: str) -> str:
    if extension in TEXT_EXTENSIONS:
        return "text"
    if extension in CODE_EXTENSIONS:
        return "code"
    if extension in IMAGE_EXTENSIONS:
        return "image"
    if extension == ".log":
        return "log"
    if extension == ".pdf":
        return "pdf"
    return "file"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _upsert_artifact(connection: Any, metadata: FileMetadata) -> ArtifactWriteResult:
    now = utc_now_iso()
    metadata_json = dumps_metadata(
        {
            "path": str(metadata.path),
            "relative_path": metadata.relative_path,
            "source": "localproof_scan",
            "extension": metadata.extension,
        }
    )
    existing = connection.execute(
        """
        SELECT id
        FROM artifacts
        WHERE sha256 = ? AND uri = ?
        """,
        (metadata.sha256, metadata.uri),
    ).fetchone()

    if existing is None:
        artifact_id = new_uuid()
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
                metadata.artifact_kind,
                metadata.uri,
                metadata.name,
                metadata.mime_type,
                metadata.sha256,
                metadata.size_bytes,
                metadata_json,
                now,
                now,
            ),
        )
        return ArtifactWriteResult(artifact_id=artifact_id, created=True)

    artifact_id = existing["id"]
    connection.execute(
        """
        UPDATE artifacts
        SET artifact_type = ?,
            name = ?,
            mime_type = ?,
            size_bytes = ?,
            metadata_json = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            metadata.artifact_kind,
            metadata.name,
            metadata.mime_type,
            metadata.size_bytes,
            metadata_json,
            now,
            artifact_id,
        ),
    )
    return ArtifactWriteResult(artifact_id=artifact_id, created=False)


def _link_artifact(connection: Any, case_id: str, artifact_id: str) -> None:
    now = utc_now_iso()
    connection.execute(
        """
        INSERT OR IGNORE INTO case_artifacts (
            case_id, artifact_id, role, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (case_id, artifact_id, "supporting", now, now),
    )


def _replace_text_chunks(connection: Any, artifact_id: str, path: Path) -> int:
    existing_rows = connection.execute(
        "SELECT rowid FROM artifact_text_chunks WHERE artifact_id = ?",
        (artifact_id,),
    ).fetchall()
    for row in existing_rows:
        connection.execute("DELETE FROM artifact_text_fts WHERE rowid = ?", (row["rowid"],))
    connection.execute("DELETE FROM artifact_text_chunks WHERE artifact_id = ?", (artifact_id,))

    chunks_created = 0
    for chunk_index, chunk in enumerate(extract_text_chunks(path)):
        now = utc_now_iso()
        metadata_json = dumps_metadata(
            {
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "source": "localproof_scan",
            }
        )
        cursor = connection.execute(
            """
            INSERT INTO artifact_text_chunks (
                id, artifact_id, chunk_index, content, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_uuid(),
                artifact_id,
                chunk_index,
                chunk.content,
                metadata_json,
                now,
                now,
            ),
        )
        rowid = cursor.lastrowid
        connection.execute(
            """
            INSERT INTO artifact_text_fts(rowid, content, artifact_id, chunk_index)
            VALUES (?, ?, ?, ?)
            """,
            (rowid, chunk.content, artifact_id, chunk_index),
        )
        chunks_created += 1

    return chunks_created

