from dataclasses import dataclass
from pathlib import Path

TEXT_EXTRACT_EXTENSIONS = {".txt", ".md", ".py", ".json", ".yaml", ".yml", ".csv", ".log"}
MAX_TEXT_EXTRACTION_BYTES = 25 * 1024 * 1024
LINES_PER_CHUNK = 200


@dataclass(frozen=True)
class TextChunk:
    content: str
    start_line: int
    end_line: int


def is_text_extractable(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTRACT_EXTENSIONS


def extract_text_chunks(path: Path, lines_per_chunk: int = LINES_PER_CHUNK) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    current_lines: list[str] = []
    chunk_start_line = 1
    current_line_number = 0

    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        for line in handle:
            current_line_number += 1
            current_lines.append(line)
            if len(current_lines) >= lines_per_chunk:
                chunks.append(
                    TextChunk(
                        content="".join(current_lines),
                        start_line=chunk_start_line,
                        end_line=current_line_number,
                    )
                )
                chunk_start_line = current_line_number + 1
                current_lines = []

    if current_lines:
        chunks.append(
            TextChunk(
                content="".join(current_lines),
                start_line=chunk_start_line,
                end_line=current_line_number,
            )
        )

    return chunks
