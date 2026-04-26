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
class GitSnapshot:
    repo_root: Path
    base_ref: str
    changed_files: list[ChangedFile]
    diff_text: str


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
    if include_untracked:
        untracked_files = _untracked_files(repo_root)
        untracked_diff = _synthetic_untracked_diff(repo_root, untracked_files)

    diff_parts = [part for part in (tracked_diff.strip(), untracked_diff.strip()) if part]
    return GitSnapshot(
        repo_root=repo_root,
        base_ref=base_ref,
        changed_files=tracked_files + untracked_files,
        diff_text="\n\n".join(diff_parts),
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


def _synthetic_untracked_diff(repo_root: Path, files: list[ChangedFile]) -> str:
    chunks: list[str] = []
    for changed_file in files:
        path = repo_root / changed_file.path
        content = _read_text_file_for_diff(path)
        if content is None:
            continue

        lines = content.splitlines()
        header = [
            f"diff --git a/{changed_file.path} b/{changed_file.path}",
            "new file mode 100644",
            "--- /dev/null",
            f"+++ b/{changed_file.path}",
            f"@@ -0,0 +1,{len(lines)} @@",
        ]
        body = [f"+{line}" for line in lines]
        chunks.append("\n".join(header + body))
    return "\n\n".join(chunks)


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
