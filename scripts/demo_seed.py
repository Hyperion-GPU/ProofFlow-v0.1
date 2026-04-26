from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import hashlib
import os
import shutil
import stat
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from proofflow.db import connect, new_uuid, utc_now_iso
from proofflow.migrations import init_db
from proofflow.models.schemas import (
    ActionCreate,
    AgentGuardReviewRequest,
    ArtifactCreate,
    CaseArtifactLinkCreate,
    CaseCreate,
    DecisionCreate,
    LocalProofScanRequest,
    LocalProofSuggestActionsRequest,
    ReportExportRequest,
)
from proofflow.services import (
    action_service,
    action_suggestion_service,
    artifact_service,
    case_service,
    decision_service,
    file_scanner,
    report_service,
    review_service,
)
from proofflow.services.json_utils import dumps_metadata

DEMO_DATA_ROOT = Path("backend") / "data" / "demo"
SAMPLE_FILES_ROOT = Path("sample_data") / "files"
SAMPLE_WORK_ROOT = Path("sample_data") / "work"
DEMO_AGENT_REPO_ROOT = Path("sample_data") / "repos" / "demo-agentguard"


@dataclass(frozen=True)
class DemoSeedResult:
    db_path: Path
    data_dir: Path
    manual_case_id: str
    localproof_case_id: str
    proof_packet_path: Path
    localproof_actions_created: int
    agentguard_case_id: str | None
    agentguard_skipped_reason: str | None


def seed_demo(
    repo_root: Path = REPO_ROOT,
    *,
    db_path: Path | None = None,
    data_dir: Path | None = None,
    include_agentguard: bool = True,
    reset: bool = True,
) -> DemoSeedResult:
    repo_root = repo_root.resolve()
    demo_data_root = (repo_root / DEMO_DATA_ROOT).resolve()
    sample_work_root = (repo_root / SAMPLE_WORK_ROOT).resolve()
    demo_agent_repo_root = (repo_root / DEMO_AGENT_REPO_ROOT).resolve()

    db_path = (db_path or demo_data_root / "proofflow.db").resolve()
    data_dir = (data_dir or demo_data_root).resolve()

    sample_files_dir = (repo_root / SAMPLE_FILES_ROOT).resolve()
    work_dir = sample_work_root
    work_files_dir = work_dir / "files"
    sorted_dir = work_dir / "sorted"
    agent_repo = demo_agent_repo_root

    _assert_at_or_under(data_dir, demo_data_root, "PROOFFLOW_DATA_DIR")
    _assert_at_or_under(db_path, data_dir, "PROOFFLOW_DB_PATH")
    _assert_at_or_under(work_dir, sample_work_root, "LocalProof work directory")
    _assert_at_or_under(agent_repo, demo_agent_repo_root, "AgentGuard demo repository")
    _ensure_sample_fixtures(sample_files_dir)

    os.environ["PROOFFLOW_DB_PATH"] = str(db_path)
    os.environ["PROOFFLOW_DATA_DIR"] = str(data_dir)

    if reset:
        _reset_demo_paths(
            (data_dir, demo_data_root, "demo data directory"),
            (work_dir, sample_work_root, "LocalProof work directory"),
            (agent_repo, demo_agent_repo_root, "AgentGuard demo repository"),
        )

    _copy_sample_files(sample_files_dir, work_files_dir)
    _prepare_sorted_dirs(sorted_dir)
    init_db(db_path)

    manual_case_id, proof_packet_path = _create_manual_demo_case(work_dir)
    scan_summary = file_scanner.scan_folder(
        LocalProofScanRequest(
            folder_path=str(work_files_dir),
            recursive=True,
            max_files=50,
        )
    )
    suggest_summary = action_suggestion_service.suggest_actions(
        LocalProofSuggestActionsRequest(
            case_id=scan_summary.case_id,
            target_root=str(sorted_dir),
        )
    )

    agentguard_case_id: str | None = None
    agentguard_skipped_reason: str | None = None
    if include_agentguard:
        agentguard_case_id, agentguard_skipped_reason = _try_create_agentguard_demo(
            agent_repo
        )

    return DemoSeedResult(
        db_path=db_path,
        data_dir=data_dir,
        manual_case_id=manual_case_id,
        localproof_case_id=scan_summary.case_id,
        proof_packet_path=proof_packet_path,
        localproof_actions_created=suggest_summary.actions_created,
        agentguard_case_id=agentguard_case_id,
        agentguard_skipped_reason=agentguard_skipped_reason,
    )


def _reset_demo_paths(*targets: tuple[Path, Path, str]) -> None:
    for path, allowed_root, label in targets:
        resolved = path.resolve()
        _assert_at_or_under(resolved, allowed_root, label)
        if resolved.exists():
            if resolved.is_dir():
                _remove_tree(resolved)
            else:
                resolved.unlink()


def _assert_at_or_under(path: Path, allowed_root: Path, label: str) -> None:
    resolved_path = path.resolve(strict=False)
    resolved_root = allowed_root.resolve(strict=False)
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as error:
        raise RuntimeError(
            f"refusing to use {label} outside allowed demo root: {resolved_path}"
        ) from error


def _remove_tree(path: Path) -> None:
    def retry_readonly(function: Any, item: str, exc_info: Any) -> None:
        try:
            os.chmod(item, stat.S_IWRITE)
            function(item)
        except OSError:
            raise exc_info[1]

    shutil.rmtree(path, onerror=retry_readonly)


def _ensure_sample_fixtures(sample_files_dir: Path) -> None:
    if not sample_files_dir.exists() or not sample_files_dir.is_dir():
        raise RuntimeError(f"sample fixture directory is missing: {sample_files_dir}")
    if not any(path.is_file() for path in sample_files_dir.rglob("*")):
        raise RuntimeError(f"sample fixture directory is empty: {sample_files_dir}")


def _copy_sample_files(source_dir: Path, destination_dir: Path) -> None:
    if destination_dir.exists():
        _remove_tree(destination_dir)
    shutil.copytree(source_dir, destination_dir)


def _prepare_sorted_dirs(sorted_dir: Path) -> None:
    for category in ("Documents", "Images", "Notes", "Code", "Logs"):
        (sorted_dir / category).mkdir(parents=True, exist_ok=True)


def _create_manual_demo_case(work_dir: Path) -> tuple[str, Path]:
    manual_dir = work_dir / "manual"
    manual_dir.mkdir(parents=True, exist_ok=True)
    note_path = manual_dir / "manual-review-note.md"
    note_content = """# Manual ProofFlow demo case

The demo case records a human-readable claim, evidence, action, and decision.
"""
    note_path.write_text(note_content, encoding="utf-8")

    case = case_service.create_case(
        CaseCreate(
            title="Demo manual proof case",
            kind="local_proof",
            status="open",
            summary="A seeded case with evidence, action, decision, and proof packet.",
            metadata={"source": "demo_seed"},
        )
    )
    artifact = artifact_service.create_artifact(
        ArtifactCreate(
            kind="note",
            uri=note_path.resolve().as_uri(),
            name=note_path.name,
            mime_type="text/markdown",
            sha256=_sha256_file(note_path),
            size_bytes=note_path.stat().st_size,
            metadata={"source": "demo_seed", "path": str(note_path.resolve())},
        )
    )
    artifact_service.link_artifact_to_case(
        case.id,
        artifact.id,
        CaseArtifactLinkCreate(role="primary"),
    )
    _insert_demo_claim_and_evidence(case.id, artifact.id)
    action_service.create_action(
        ActionCreate(
            case_id=case.id,
            kind="manual_check",
            title="Review seeded evidence",
            reason="Confirm the demo note is sufficient for a manual proof packet.",
            metadata={"source": "demo_seed"},
        )
    )
    decision_service.create_decision(
        case.id,
        DecisionCreate(
            title="Accept demo evidence packet",
            status="accepted",
            rationale="The seeded note and evidence quote are present and reproducible.",
            result="Use this case as a quick UI smoke sample.",
        ),
    )
    report = report_service.export_case_report(
        case.id,
        ReportExportRequest(format="markdown"),
    )
    return case.id, Path(report.path)


def _insert_demo_claim_and_evidence(case_id: str, artifact_id: str) -> None:
    now = utc_now_iso()
    claim_id = new_uuid()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO claims (
                id, case_id, run_id, claim_text, claim_type, status,
                metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                claim_id,
                case_id,
                None,
                "ProofFlow demo data can be reviewed locally with citations.",
                "demo_claim",
                "open",
                dumps_metadata({"severity": "info", "source": "demo_seed"}),
                now,
                now,
            ),
        )
        connection.execute(
            """
            INSERT INTO evidence (
                id, case_id, artifact_id, claim_id, evidence_type, content,
                source_ref, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_uuid(),
                case_id,
                artifact_id,
                claim_id,
                "note_quote",
                "The demo case records a human-readable claim, evidence, action, and decision.",
                "manual-review-note.md:3",
                dumps_metadata({"source": "demo_seed"}),
                now,
                now,
            ),
        )
        connection.commit()


def _try_create_agentguard_demo(agent_repo: Path) -> tuple[str | None, str | None]:
    if shutil.which("git") is None:
        return None, "git executable was not found"
    try:
        _create_demo_git_repo(agent_repo)
        command = f'"{sys.executable}" run_tests.py'
        response = review_service.review_repository(
            AgentGuardReviewRequest(
                repo_path=str(agent_repo),
                base_ref="HEAD",
                include_untracked=True,
                test_command=command,
            )
        )
        return response.case_id, None
    except Exception as error:  # Demo mode should continue even if local git is unusual.
        return None, f"{error.__class__.__name__}: {error}"


def _create_demo_git_repo(agent_repo: Path) -> None:
    if agent_repo.exists():
        _remove_tree(agent_repo)
    agent_repo.mkdir(parents=True, exist_ok=True)
    (agent_repo / "actions").mkdir()
    (agent_repo / "actions" / "file_ops.py").write_text(
        """from pathlib import Path


def target_name(path: str) -> str:
    return Path(path).name
""",
        encoding="utf-8",
    )
    (agent_repo / "run_tests.py").write_text(
        "print('demo tests passed')\nraise SystemExit(0)\n",
        encoding="utf-8",
    )

    _git(agent_repo, "init")
    _git(agent_repo, "config", "user.email", "prooflow-demo@example.test")
    _git(agent_repo, "config", "user.name", "ProofFlow Demo")
    _git(agent_repo, "add", ".")
    _git(agent_repo, "commit", "-m", "baseline")

    (agent_repo / "actions" / "file_ops.py").write_text(
        """from pathlib import Path
import shutil


def target_name(path: str) -> str:
    return Path(path).name


def move_preview_only(source: str, destination: str) -> str:
    return f"would move {Path(source).name} to {Path(destination)} with shutil.move"
""",
        encoding="utf-8",
    )
    (agent_repo / "review-notes.md").write_text(
        "Untracked review note for AgentGuard demo.\n",
        encoding="utf-8",
    )


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        timeout=30,
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _print_next_steps(result: DemoSeedResult, repo_root: Path) -> None:
    backend_dir = repo_root / "backend"
    frontend_dir = repo_root / "frontend"
    print("ProofFlow demo seed complete.")
    print()
    print(f"Demo DB: {result.db_path}")
    print(f"Demo data dir: {result.data_dir}")
    print(f"Manual case: {result.manual_case_id}")
    print(f"LocalProof case: {result.localproof_case_id}")
    print(f"LocalProof actions created: {result.localproof_actions_created}")
    if result.agentguard_case_id:
        print(f"AgentGuard case: {result.agentguard_case_id}")
    else:
        print(f"AgentGuard skipped: {result.agentguard_skipped_reason}")
    print(f"Proof Packet: {result.proof_packet_path}")
    print()
    print("Backend command:")
    print(
        f'cd "{backend_dir}"; '
        f'$env:PROOFFLOW_DB_PATH="{result.db_path}"; '
        f'$env:PROOFFLOW_DATA_DIR="{result.data_dir}"; '
        "python -m uvicorn proofflow.main:app --host 127.0.0.1 --port 8787"
    )
    print()
    print("Frontend command:")
    print(f'cd "{frontend_dir}"; npm run dev')


def main() -> None:
    result = seed_demo()
    _print_next_steps(result, REPO_ROOT)


if __name__ == "__main__":
    main()
