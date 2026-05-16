from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from proofflow.db import connect
from proofflow.migrations import init_db
from proofflow.models.schemas import AgentGuardReviewRequest, ReportExportRequest
from proofflow.services.json_utils import dumps_metadata, loads_metadata
from proofflow.services.report_service import export_case_report
from proofflow.services.review_service import review_repository


DEFAULT_OUTPUT_DIR = "prooflow-ci-output"
DEFAULT_ARTIFACT_NAME = "proofflow-agentguard-review"
SUMMARY_SCHEMA_VERSION = "2"
TEST_COMMAND_POLICY = "not_run_by_ci_design"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = _resolve_repo_root(args.repo_root)
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    ci_context = _ci_context(args, repo_root)
    summary: dict[str, Any] = _empty_summary(args.artifact_name, ci_context)
    try:
        _configure_isolated_instance(output_dir)
        init_db()

        review = review_repository(
            AgentGuardReviewRequest(
                repo_path=str(repo_root),
                base_ref=args.base_ref,
                include_untracked=args.include_untracked,
            )
        )
        summary.update(
            {
                "case_id": review.case_id,
                "risk_level": review.risk_level,
                "changed_files": len(review.changed_files),
                "changed_file_paths": review.changed_files,
                "claims_created": review.claims_created,
                "evidence_created": review.evidence_created,
            }
        )
        exported_artifacts = _export_review_artifacts(output_dir, review.case_id)
        _attach_ci_metadata(review.case_id, ci_context, args, exported_artifacts)
        packet = export_case_report(
            review.case_id,
            ReportExportRequest(format="markdown"),
        )
        packet_path = Path(packet.path)
        packet_record = _artifact_manifest_entry(
            artifact_id=packet.artifact_id,
            kind="proof_packet",
            name=packet.filename,
            path=packet_path,
            output_dir=output_dir,
        )
        manifest_path = _write_artifact_manifest(
            output_dir,
            exported_artifacts + [packet_record],
        )
        summary.update(
            {
                "proof_packet_path": packet.path,
                "proof_packet_relative_path": _relative_path(output_dir, packet_path),
                "artifact_manifest_path": _relative_path(output_dir, manifest_path),
                "diff_artifact_path": _first_relative_path(exported_artifacts, "git_diff"),
                "status": "completed",
                "error": None,
            }
        )
    except Exception as error:  # noqa: BLE001 - CI summary must preserve root cause.
        summary.update(
            {
                "status": "failed",
                "error": f"{type(error).__name__}: {error}",
            }
        )
    finally:
        _write_summary(output_dir / "summary.json", summary)

    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an isolated AgentGuard review and export a Proof Packet."
    )
    parser.add_argument(
        "--repo-root",
        default=os.getenv("PROOFFLOW_CI_REPO_ROOT"),
        help="Git repository root. Defaults to the current repository root.",
    )
    parser.add_argument(
        "--base-ref",
        default=os.getenv("PROOFFLOW_CI_BASE_REF", "HEAD"),
        help="Base git ref or SHA for the diff.",
    )
    parser.add_argument(
        "--output-dir",
        default=os.getenv("PROOFFLOW_CI_OUTPUT_DIR", DEFAULT_OUTPUT_DIR),
        help=f"Output directory. Defaults to {DEFAULT_OUTPUT_DIR}/.",
    )
    parser.add_argument(
        "--artifact-name",
        default=os.getenv("PROOFFLOW_CI_ARTIFACT_NAME", DEFAULT_ARTIFACT_NAME),
        help="Workflow artifact name to include in summary output.",
    )
    parser.add_argument(
        "--include-untracked",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Include untracked files in the review diff.",
    )
    return parser.parse_args(argv)


def _resolve_repo_root(raw_repo_root: str | None) -> Path:
    if raw_repo_root:
        return Path(raw_repo_root).expanduser().resolve()

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip()).resolve()
    return Path.cwd().resolve()


def _ci_context(args: argparse.Namespace, repo_root: Path) -> dict[str, Any]:
    repo = os.getenv("PROOFFLOW_CI_REPO") or os.getenv("GITHUB_REPOSITORY") or repo_root.name
    run_id = os.getenv("PROOFFLOW_CI_RUN_ID") or os.getenv("GITHUB_RUN_ID")
    server_url = os.getenv("GITHUB_SERVER_URL", "https://github.com")
    workflow_run_url = os.getenv("PROOFFLOW_CI_RUN_URL")
    if not workflow_run_url and run_id and repo:
        workflow_run_url = f"{server_url}/{repo}/actions/runs/{run_id}"

    return {
        "generated_at": _utc_now(),
        "repo": repo,
        "pr_number": os.getenv("PROOFFLOW_CI_PR_NUMBER"),
        "workflow_run_id": run_id,
        "workflow_run_url": workflow_run_url,
        "base_sha": os.getenv("PROOFFLOW_CI_BASE_SHA") or args.base_ref,
        "head_sha": os.getenv("PROOFFLOW_CI_HEAD_SHA") or _git_rev_parse(repo_root, "HEAD"),
        "base_ref": args.base_ref,
    }


def _git_rev_parse(repo_root: Path, ref: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", ref],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _configure_isolated_instance(output_dir: Path) -> None:
    data_dir = output_dir / "data"
    os.environ["PROOFFLOW_DB_PATH"] = str(output_dir / "proofflow-ci.db")
    os.environ["PROOFFLOW_DATA_DIR"] = str(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)


def _empty_summary(artifact_name: str, ci_context: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        **ci_context,
        "case_id": None,
        "risk_level": "unknown",
        "changed_files": 0,
        "changed_file_paths": [],
        "claims_created": 0,
        "evidence_created": 0,
        "proof_packet_path": None,
        "proof_packet_relative_path": None,
        "artifact_manifest_path": None,
        "diff_artifact_path": None,
        "artifact_name": artifact_name,
        "test_status": "not_run",
        "test_command_policy": TEST_COMMAND_POLICY,
        "status": "failed",
        "error": None,
    }


def _write_summary(path: Path, summary: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _export_review_artifacts(output_dir: Path, case_id: str) -> list[dict[str, Any]]:
    artifacts_dir = output_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    git_diff = _load_text_artifact(case_id, "git_diff")
    if git_diff is None:
        return []

    diff_path = artifacts_dir / "git-diff.patch"
    diff_path.write_text(git_diff["content"], encoding="utf-8")
    record = _artifact_manifest_entry(
        artifact_id=git_diff["id"],
        kind=git_diff["kind"],
        name=git_diff["name"],
        path=diff_path,
        output_dir=output_dir,
    )
    _update_artifact_metadata(
        git_diff["id"],
        {
            "artifact_relative_path": record["relative_path"],
            "artifact_sha256": record["sha256"],
            "artifact_size_bytes": record["size_bytes"],
        },
        sha256=record["sha256"],
        size_bytes=record["size_bytes"],
    )
    return [record]


def _load_text_artifact(case_id: str, artifact_type: str) -> dict[str, Any] | None:
    with connect() as connection:
        artifact = connection.execute(
            """
            SELECT artifacts.id, artifacts.artifact_type, artifacts.name
            FROM artifacts
            JOIN case_artifacts ON case_artifacts.artifact_id = artifacts.id
            WHERE case_artifacts.case_id = ?
              AND artifacts.artifact_type = ?
            ORDER BY artifacts.created_at ASC, artifacts.id ASC
            LIMIT 1
            """,
            (case_id, artifact_type),
        ).fetchone()
        if artifact is None:
            return None
        chunks = connection.execute(
            """
            SELECT content
            FROM artifact_text_chunks
            WHERE artifact_id = ?
            ORDER BY chunk_index ASC
            """,
            (artifact["id"],),
        ).fetchall()
    return {
        "id": artifact["id"],
        "kind": artifact["artifact_type"],
        "name": artifact["name"],
        "content": "\n".join(row["content"] for row in chunks),
    }


def _attach_ci_metadata(
    case_id: str,
    ci_context: dict[str, Any],
    args: argparse.Namespace,
    exported_artifacts: list[dict[str, Any]],
) -> None:
    provenance = {
        **ci_context,
        "include_untracked": args.include_untracked,
        "test_command_policy": TEST_COMMAND_POLICY,
        "diff_artifact_path": _first_relative_path(exported_artifacts, "git_diff"),
    }
    with connect() as connection:
        case_row = connection.execute(
            "SELECT metadata_json FROM cases WHERE id = ?",
            (case_id,),
        ).fetchone()
        if case_row is not None:
            metadata = loads_metadata(case_row["metadata_json"])
            metadata["ci_provenance"] = provenance
            metadata["test_command_policy"] = TEST_COMMAND_POLICY
            connection.execute(
                "UPDATE cases SET metadata_json = ?, updated_at = ? WHERE id = ?",
                (dumps_metadata(metadata), _utc_now(), case_id),
            )

        run_rows = connection.execute(
            "SELECT id, metadata_json FROM runs WHERE case_id = ?",
            (case_id,),
        ).fetchall()
        for run_row in run_rows:
            metadata = loads_metadata(run_row["metadata_json"])
            metadata["ci_provenance"] = provenance
            metadata["test_command_policy"] = TEST_COMMAND_POLICY
            connection.execute(
                "UPDATE runs SET metadata_json = ?, updated_at = ? WHERE id = ?",
                (dumps_metadata(metadata), _utc_now(), run_row["id"]),
            )
        connection.commit()


def _update_artifact_metadata(
    artifact_id: str,
    updates: dict[str, Any],
    *,
    sha256: str | None = None,
    size_bytes: int | None = None,
) -> None:
    with connect() as connection:
        row = connection.execute(
            "SELECT metadata_json FROM artifacts WHERE id = ?",
            (artifact_id,),
        ).fetchone()
        if row is None:
            return
        metadata = loads_metadata(row["metadata_json"])
        metadata.update(updates)
        assignments = ["metadata_json = ?", "updated_at = ?"]
        values: list[Any] = [dumps_metadata(metadata), _utc_now()]
        if sha256 is not None:
            assignments.append("sha256 = ?")
            values.append(sha256)
        if size_bytes is not None:
            assignments.append("size_bytes = ?")
            values.append(size_bytes)
        values.append(artifact_id)
        connection.execute(
            f"UPDATE artifacts SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        connection.commit()


def _write_artifact_manifest(
    output_dir: Path,
    artifacts: list[dict[str, Any]],
) -> Path:
    manifest_path = output_dir / "artifacts" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "1",
        "generated_at": _utc_now(),
        "artifacts": artifacts,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def _artifact_manifest_entry(
    *,
    artifact_id: str,
    kind: str,
    name: str,
    path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    content = path.read_bytes()
    return {
        "artifact_id": artifact_id,
        "kind": kind,
        "name": name,
        "relative_path": _relative_path(output_dir, path),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content),
    }


def _relative_path(root: Path, path: Path) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return path.name
    return relative.as_posix()


def _first_relative_path(artifacts: list[dict[str, Any]], kind: str) -> str | None:
    for artifact in artifacts:
        if artifact.get("kind") == kind:
            return str(artifact.get("relative_path"))
    return None


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
