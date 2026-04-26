from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import subprocess


class GitServiceError(ValueError):
    """Raised when AgentGuard cannot inspect a local git repository."""


@dataclass(frozen=True)
class ChangedFile:
    path: str
    status: str
    source: str


@dataclass(frozen=True)
class UntrackedFilePolicyNote:
    path: str
    reason: str
    size_bytes: int | None = None
    cap_bytes: int | None = None
    truncated: bool = False


@dataclass(frozen=True)
class GitSnapshot:
    repo_root: Path
    base_ref: str
    changed_files: list[ChangedFile]
    diff_text: str
    untracked_policy_notes: list[UntrackedFilePolicyNote]


SENSITIVE_UNTRACKED_EXACT_NAMES = {".env", ".env.local", ".env.production"}
SENSITIVE_UNTRACKED_SUFFIXES = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".db",
    ".sqlite",
    ".sqlite3",
}
UNTRACKED_TEXT_DIFF_SIZE_CAP_BYTES = 256 * 1024


def inspect_working_tree(
    repo_path: str,
    base_ref: str = "HEAD",
    include_untracked: bool = True,
) -> GitSnapshot:
    repo_root = resolve_repo_root(repo_path)
    tracked_files = _tracked_changed_files(repo_root, base_ref)
    tracked_diff = _tracked_diff(repo_root, base_ref)

    untracked_files: list[ChangedFile] = []
    untracked_diff = ""
    untracked_policy_notes: list[UntrackedFilePolicyNote] = []
    if include_untracked:
        untracked_files = _untracked_files(repo_root)
        untracked_diff, untracked_policy_notes = _synthetic_untracked_diff(
            repo_root,
            untracked_files,
        )

    diff_parts = [part for part in (tracked_diff.strip(), untracked_diff.strip()) if part]
    return GitSnapshot(
        repo_root=repo_root,
        base_ref=base_ref,
        changed_files=tracked_files + untracked_files,
        diff_text="\n\n".join(diff_parts),
        untracked_policy_notes=untracked_policy_notes,
    )


def resolve_repo_root(repo_path: str) -> Path:
    path = Path(repo_path).expanduser()
    if not path.exists() or not path.is_dir():
        raise GitServiceError(f"repo_path is not a directory: {repo_path}")

    result = _run_git(path, ["rev-parse", "--show-toplevel"])
    root = result.stdout.strip()
    if not root:
        raise GitServiceError(f"repo_path is not a git repository: {repo_path}")
    return Path(root).resolve()


def _tracked_changed_files(repo_root: Path, base_ref: str) -> list[ChangedFile]:
    result = _run_git(repo_root, ["diff", "--name-status", base_ref, "--"])
    files: list[ChangedFile] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status = parts[0]
        path = parts[-1]
        files.append(ChangedFile(path=path, status=status, source="tracked"))
    return files


def _tracked_diff(repo_root: Path, base_ref: str) -> str:
    result = _run_git(
        repo_root,
        ["diff", "--no-ext-diff", "--unified=3", base_ref, "--"],
    )
    return result.stdout


def _untracked_files(repo_root: Path) -> list[ChangedFile]:
    result = _run_git(repo_root, ["ls-files", "--others", "--exclude-standard"])
    return [
        ChangedFile(path=line.strip(), status="A?", source="untracked")
        for line in result.stdout.splitlines()
        if line.strip()
    ]


def _synthetic_untracked_diff(
    repo_root: Path,
    files: list[ChangedFile],
) -> tuple[str, list[UntrackedFilePolicyNote]]:
    chunks: list[str] = []
    notes: list[UntrackedFilePolicyNote] = []
    for changed_file in files:
        path = repo_root / changed_file.path
        size_bytes = _safe_file_size(path)

        if _is_sensitive_untracked_path(changed_file.path):
            notes.append(
                UntrackedFilePolicyNote(
                    path=changed_file.path,
                    reason="sensitive_untracked_file",
                    size_bytes=size_bytes,
                )
            )
            continue

        if size_bytes is not None and size_bytes > UNTRACKED_TEXT_DIFF_SIZE_CAP_BYTES:
            placeholder = (
                "[ProofFlow omitted untracked file content: "
                f"file exceeds {UNTRACKED_TEXT_DIFF_SIZE_CAP_BYTES} bytes]"
            )
            notes.append(
                UntrackedFilePolicyNote(
                    path=changed_file.path,
                    reason="untracked_file_exceeds_diff_cap",
                    size_bytes=size_bytes,
                    cap_bytes=UNTRACKED_TEXT_DIFF_SIZE_CAP_BYTES,
                    truncated=True,
                )
            )
            chunks.append(_new_file_diff(changed_file.path, [placeholder]))
            continue

        content = _read_text_file_for_diff(path)
        if content is None:
            continue

        chunks.append(_new_file_diff(changed_file.path, content.splitlines()))
    return "\n\n".join(chunks), notes


def _new_file_diff(path: str, lines: list[str]) -> str:
    header = [
        f"diff --git a/{path} b/{path}",
        "new file mode 100644",
        "--- /dev/null",
        f"+++ b/{path}",
        f"@@ -0,0 +1,{len(lines)} @@",
    ]
    body = [f"+{line}" for line in lines]
    return "\n".join(header + body)


def _safe_file_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None


def _is_sensitive_untracked_path(path: str) -> bool:
    name = Path(path).name.lower()
    suffix = Path(path).suffix.lower()
    return name in SENSITIVE_UNTRACKED_EXACT_NAMES or suffix in SENSITIVE_UNTRACKED_SUFFIXES


def _read_text_file_for_diff(path: Path) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in raw:
        return None
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


def _run_git(repo_root: Path, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except FileNotFoundError as error:
        raise GitServiceError("git executable was not found") from error
    except subprocess.TimeoutExpired as error:
        raise GitServiceError("git command timed out") from error

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "git command failed"
        raise GitServiceError(message)
    return result
