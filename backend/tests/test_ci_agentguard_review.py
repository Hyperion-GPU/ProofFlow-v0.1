from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci_agentguard_review.py"


def _load_ci_script():
    spec = importlib.util.spec_from_file_location("ci_agentguard_review", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _require_git() -> None:
    if shutil.which("git") is None:
        pytest.skip("git executable is not available")


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return result.stdout.strip()


def _init_repo(repo: Path) -> str:
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "ci-agentguard@example.test")
    _git(repo, "config", "user.name", "CI AgentGuard Test")
    (repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")
    return _git(repo, "rev-parse", "HEAD")


def _read_summary(output_dir: Path) -> dict:
    return json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))


def test_ci_script_generates_summary_and_proof_packet_for_changed_repo(tmp_path):
    _require_git()
    module = _load_ci_script()
    repo = tmp_path / "repo"
    base_ref = _init_repo(repo)
    output_dir = tmp_path / "ci-output"

    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    exit_code = module.main(
        [
            "--repo-root",
            str(repo),
            "--base-ref",
            base_ref,
            "--output-dir",
            str(output_dir),
        ]
    )

    summary = _read_summary(output_dir)
    packet_path = Path(summary["proof_packet_path"])
    assert exit_code == 0
    assert summary["status"] == "completed"
    assert summary["risk_level"] in {"info", "low", "medium", "high"}
    assert summary["changed_files"] == 1
    assert summary["changed_file_paths"] == ["app.py"]
    assert summary["claims_created"] >= 1
    assert summary["evidence_created"] == summary["claims_created"]
    assert packet_path.exists()
    assert packet_path.read_text(encoding="utf-8").startswith("# Proof Packet:")
    assert output_dir in packet_path.parents
    assert (output_dir / "proofflow-ci.db").exists()


def test_ci_script_generates_low_risk_summary_when_no_changes(tmp_path):
    _require_git()
    module = _load_ci_script()
    repo = tmp_path / "repo"
    base_ref = _init_repo(repo)
    output_dir = tmp_path / "ci-output"

    exit_code = module.main(
        [
            "--repo-root",
            str(repo),
            "--base-ref",
            base_ref,
            "--output-dir",
            str(output_dir),
        ]
    )

    summary = _read_summary(output_dir)
    assert exit_code == 0
    assert summary["status"] == "completed"
    assert summary["risk_level"] == "low"
    assert summary["changed_files"] == 0
    assert summary["changed_file_paths"] == []
    assert Path(summary["proof_packet_path"]).exists()


def test_ci_script_records_failed_review_summary(tmp_path, monkeypatch):
    module = _load_ci_script()
    output_dir = tmp_path / "ci-output"

    def fail_review(_payload):
        raise RuntimeError("simulated review failure")

    monkeypatch.setattr(module, "review_repository", fail_review)

    exit_code = module.main(
        [
            "--repo-root",
            str(tmp_path),
            "--base-ref",
            "HEAD",
            "--output-dir",
            str(output_dir),
        ]
    )

    summary = _read_summary(output_dir)
    assert exit_code == 0
    assert summary["status"] == "failed"
    assert summary["proof_packet_path"] is None
    assert "simulated review failure" in summary["error"]
