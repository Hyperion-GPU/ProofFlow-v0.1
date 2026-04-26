from typing import Any

import re

from proofflow.db import connect
from proofflow.models.schemas import SearchResponse, SearchResult
from proofflow.services.json_utils import loads_metadata

TOKEN_RE = re.compile(r"\w+(?:-\w+)*", re.UNICODE)
DEFAULT_LIMIT = 25
MAX_LIMIT = 25


class SearchQueryError(ValueError):
    """Raised when a search query cannot be converted to safe FTS tokens."""


def search_chunks(query: str, limit: int = DEFAULT_LIMIT) -> SearchResponse:
    match_query = _to_match_query(query)
    result_limit = max(1, min(limit, MAX_LIMIT))

    with connect() as connection:
        rows = connection.execute(
            """
            SELECT
                artifacts.id AS artifact_id,
                artifact_text_chunks.id AS chunk_id,
                artifacts.name AS name,
                artifacts.metadata_json AS artifact_metadata_json,
                artifact_text_chunks.metadata_json AS chunk_metadata_json,
                snippet(artifact_text_fts, 0, '[', ']', ' ... ', 32) AS snippet,
                bm25(artifact_text_fts) AS raw_score
            FROM artifact_text_fts
            JOIN artifact_text_chunks
                ON artifact_text_chunks.rowid = artifact_text_fts.rowid
            JOIN artifacts
                ON artifacts.id = artifact_text_chunks.artifact_id
            WHERE artifact_text_fts MATCH ?
            ORDER BY raw_score ASC
            LIMIT ?
            """,
            (match_query, result_limit),
        ).fetchall()

    return SearchResponse(
        query=query,
        results=[_result_from_row(row) for row in rows],
    )


def _to_match_query(query: str) -> str:
    if not query or not query.strip():
        raise SearchQueryError("search query cannot be empty")

    tokens = TOKEN_RE.findall(query)
    if not tokens:
        raise SearchQueryError("search query does not contain searchable terms")

    return " ".join(f'"{token}"' for token in tokens)


def _result_from_row(row: Any) -> SearchResult:
    artifact_metadata = loads_metadata(row["artifact_metadata_json"])
    chunk_metadata = loads_metadata(row["chunk_metadata_json"])

    return SearchResult(
        artifact_id=row["artifact_id"],
        chunk_id=row["chunk_id"],
        name=row["name"],
        path=_string_or_none(artifact_metadata.get("path")),
        snippet=_compact_snippet(row["snippet"]),
        start_line=_positive_int_or_default(chunk_metadata.get("start_line"), 1),
        end_line=_positive_int_or_default(chunk_metadata.get("end_line"), 1),
        score=-float(row["raw_score"]),
    )


def _string_or_none(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _positive_int_or_default(value: Any, default: int) -> int:
    if isinstance(value, int) and value > 0:
        return value
    return default


def _compact_snippet(snippet: str | None) -> str:
    if not snippet:
        return ""
    return " ".join(snippet.split())

