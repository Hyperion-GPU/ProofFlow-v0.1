from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from proofflow.migrations import init_db
from proofflow.models.schemas import AgentGuardReviewRequest, ReportExportRequest
from proofflow.services.report_service import export_case_report
from proofflow.services.review_service import review_repository


DEFAULT_OUTPUT_DIR = "prooflow-ci-output"
DEFAULT_ARTIFACT_NAME = "proofflow-agentguard-review"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = _resolve_repo_root(args.repo_root)
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = _empty_summary(args.artifact_name)
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
        packet = export_case_report(
            review.case_id,
            ReportExportRequest(format="markdown"),
        )
        summary.update(
            {
                "proof_packet_path": packet.path,
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


def _configure_isolated_instance(output_dir: Path) -> None:
    data_dir = output_dir / "data"
    os.environ["PROOFFLOW_DB_PATH"] = str(output_dir / "proofflow-ci.db")
    os.environ["PROOFFLOW_DATA_DIR"] = str(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)


def _empty_summary(artifact_name: str) -> dict[str, Any]:
    return {
        "case_id": None,
        "risk_level": "unknown",
        "changed_files": 0,
        "changed_file_paths": [],
        "claims_created": 0,
        "evidence_created": 0,
        "proof_packet_path": None,
        "artifact_name": artifact_name,
        "status": "failed",
        "error": None,
    }


def _write_summary(path: Path, summary: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
