from pathlib import Path
from typing import Any

from proofflow.db import connect, new_uuid, utc_now_iso
from proofflow.models.schemas import (
    ActionResponse,
    LocalProofSuggestActionsRequest,
    LocalProofSuggestActionsSummary,
    LocalProofSuggestSkippedItem,
)
from proofflow.services import action_service
from proofflow.services.errors import NotFoundError
from proofflow.services.json_utils import dumps_metadata, loads_metadata

PDF_KEYWORDS = ("invoice", "receipt", "bill")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
NOTE_EXTENSIONS = {".md", ".txt"}
CODE_EXTENSIONS = {".py", ".json", ".yaml", ".yml"}


class SuggestActionsError(ValueError):
    """Raised when LocalProof cannot safely build action suggestions."""


def suggest_actions(request: LocalProofSuggestActionsRequest) -> LocalProofSuggestActionsSummary:
    target_root = _validate_target_root(request.target_root)
    used_destinations: set[str] = set()
    mkdir_action_ids: dict[str, str] = {}
    skipped_items: list[LocalProofSuggestSkippedItem] = []
    action_ids: list[str] = []

    with connect() as connection:
        _ensure_case_exists(connection, request.case_id)
        rows = connection.execute(
            """
            SELECT
                artifacts.id,
                artifacts.artifact_type,
                artifacts.name,
                artifacts.metadata_json,
                artifacts.created_at
            FROM case_artifacts
            JOIN artifacts ON artifacts.id = case_artifacts.artifact_id
            WHERE case_artifacts.case_id = ?
            ORDER BY artifacts.created_at ASC, artifacts.id ASC
            """,
            (request.case_id,),
        ).fetchall()

        for row in rows:
            metadata = loads_metadata(row["metadata_json"])
            source_path, skip_reason = _source_path_from_metadata(metadata)
            if skip_reason is not None:
                skipped_items.append(_skipped(row, metadata.get("path"), skip_reason))
                continue

            category_rule = _category_for_artifact(row, source_path)
            if category_rule is None:
                skipped_items.append(_skipped(row, str(source_path), "unsupported_file_type"))
                continue

            category, rule = category_rule
            destination = _next_available_destination(
                target_root / category,
                source_path.name,
                used_destinations,
            )
            _ensure_inside_target_root(destination, target_root)
            depends_on_action_id = None
            destination_dir = target_root / category
            if not destination_dir.exists():
                depends_on_action_id = mkdir_action_ids.get(category)
                if depends_on_action_id is None:
                    depends_on_action_id = _insert_pending_mkdir_action(
                        connection=connection,
                        case_id=request.case_id,
                        dir_path=destination_dir,
                        category=category,
                    )
                    mkdir_action_ids[category] = depends_on_action_id
                    action_ids.append(depends_on_action_id)

            action_ids.append(
                _insert_pending_move_action(
                    connection=connection,
                    case_id=request.case_id,
                    artifact_id=row["id"],
                    source_path=source_path,
                    destination_path=destination,
                    category=category,
                    rule=rule,
                    depends_on_action_id=depends_on_action_id,
                )
            )

        connection.commit()

    actions = [action_service.get_action(action_id) for action_id in action_ids]
    return LocalProofSuggestActionsSummary(
        case_id=request.case_id,
        target_root=str(target_root),
        actions_created=len(actions),
        skipped=len(skipped_items),
        skipped_items=skipped_items,
        actions=actions,
    )


def _validate_target_root(raw_target_root: str) -> Path:
    target_root = Path(raw_target_root).expanduser()
    if target_root.exists() and not target_root.is_dir():
        raise SuggestActionsError("target_root exists but is not a directory")
    return target_root.resolve(strict=False)


def _ensure_case_exists(connection: Any, case_id: str) -> None:
    row = connection.execute("SELECT 1 FROM cases WHERE id = ?", (case_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"case not found: {case_id}")


def _source_path_from_metadata(metadata: dict[str, Any]) -> tuple[Path, str | None]:
    raw_path = metadata.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        return Path(), "missing_source_path"

    source_path = Path(raw_path).expanduser()
    if source_path.is_symlink():
        return source_path, "source_path_symlink"
    if not source_path.exists():
        return source_path, "source_path_missing"
    if not source_path.is_file():
        return source_path, "source_path_not_file"
    return source_path.resolve(strict=False), None


def _category_for_artifact(row: Any, source_path: Path) -> tuple[str, str] | None:
    extension = source_path.suffix.lower()
    artifact_kind = row["artifact_type"]
    name_lower = source_path.name.lower()

    if artifact_kind == "pdf" or extension == ".pdf":
        if any(keyword in name_lower for keyword in PDF_KEYWORDS):
            return "Documents", "pdf_financial_document"
        return None
    if artifact_kind == "image" or extension in IMAGE_EXTENSIONS:
        return "Images", "image"
    if extension in NOTE_EXTENSIONS:
        return "Notes", "note"
    if extension in CODE_EXTENSIONS:
        return "Code", "code"
    if artifact_kind == "log" or extension == ".log":
        return "Logs", "log"
    return None


def _next_available_destination(
    destination_dir: Path,
    filename: str,
    used_destinations: set[str],
) -> Path:
    original = Path(filename)
    stem = original.stem
    suffix = original.suffix
    candidate = destination_dir / filename
    index = 1

    while candidate.exists() or _destination_key(candidate) in used_destinations:
        candidate = destination_dir / f"{stem}-{index}{suffix}"
        index += 1

    used_destinations.add(_destination_key(candidate))
    return candidate.resolve(strict=False)


def _destination_key(path: Path) -> str:
    return str(path.resolve(strict=False)).casefold()


def _ensure_inside_target_root(destination: Path, target_root: Path) -> None:
    try:
        destination.resolve(strict=False).relative_to(target_root.resolve(strict=False))
    except ValueError as error:
        raise SuggestActionsError("proposed destination is outside target_root") from error


def _insert_pending_move_action(
    *,
    connection: Any,
    case_id: str,
    artifact_id: str,
    source_path: Path,
    destination_path: Path,
    category: str,
    rule: str,
    depends_on_action_id: str | None,
) -> str:
    now = utc_now_iso()
    action_id = new_uuid()
    title = f"Move {source_path.name} to {category}"
    reason = f"Deterministic LocalProof rule: {rule}"
    preview = {
        "from_path": str(source_path),
        "to_path": str(destination_path),
    }
    metadata = {
        "source": "localproof_suggest_actions",
        "artifact_id": artifact_id,
        "category": category,
        "rule": rule,
    }
    if depends_on_action_id is not None:
        metadata["depends_on_action_id"] = depends_on_action_id
        metadata["depends_on_dir_path"] = str(destination_path.parent)

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
            case_id,
            None,
            "move_file",
            "pending",
            title,
            title,
            reason,
            dumps_metadata(preview),
            None,
            None,
            dumps_metadata(metadata),
            now,
            now,
        ),
    )
    return action_id


def _insert_pending_mkdir_action(
    *,
    connection: Any,
    case_id: str,
    dir_path: Path,
    category: str,
) -> str:
    now = utc_now_iso()
    action_id = new_uuid()
    title = f"Create {category} directory"
    reason = "Deterministic LocalProof prerequisite: destination directory"
    preview = {
        "dir_path": str(dir_path.resolve(strict=False)),
    }
    metadata = {
        "source": "localproof_suggest_actions",
        "category": category,
        "rule": "missing_destination_directory",
    }

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
            case_id,
            None,
            "mkdir_dir",
            "pending",
            title,
            title,
            reason,
            dumps_metadata(preview),
            None,
            None,
            dumps_metadata(metadata),
            now,
            now,
        ),
    )
    return action_id


def _skipped(row: Any, path: Any, reason: str) -> LocalProofSuggestSkippedItem:
    return LocalProofSuggestSkippedItem(
        artifact_id=row["id"],
        path=path if isinstance(path, str) else None,
        reason=reason,
    )
