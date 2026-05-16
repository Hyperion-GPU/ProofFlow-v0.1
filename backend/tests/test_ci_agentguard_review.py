from __future__ import annotations

import importlib.util
import hashlib
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


def _read_manifest(output_dir: Path) -> dict:
    return json.loads((output_dir / "artifacts" / "manifest.json").read_text(encoding="utf-8"))


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
    assert summary["schema_version"] == "2"
    assert summary["status"] == "completed"
    assert summary["risk_level"] in {"info", "low", "medium", "high"}
    assert summary["changed_files"] == 1
    assert summary["changed_file_paths"] == ["app.py"]
    assert summary["claims_created"] >= 1
    assert summary["evidence_created"] == summary["claims_created"]
    assert summary["base_sha"] == base_ref
    assert summary["head_sha"]
    assert summary["test_status"] == "not_run"
    assert summary["test_command_policy"] == "not_run_by_ci_design"
    assert summary["diff_artifact_path"] == "artifacts/git-diff.patch"
    assert summary["artifact_manifest_path"] == "artifacts/manifest.json"
    assert summary["proof_packet_relative_path"].startswith("data/proof_packets/")
    assert packet_path.exists()
    packet_text = packet_path.read_text(encoding="utf-8")
    assert packet_text.startswith("# Proof Packet:")
    assert "## CI Provenance" in packet_text
    assert "artifacts/git-diff.patch" in packet_text
    assert "not_run_by_ci_design" in packet_text
    assert output_dir in packet_path.parents
    assert (output_dir / "proofflow-ci.db").exists()

    diff_path = output_dir / "artifacts" / "git-diff.patch"
    assert diff_path.exists()
    diff_text = diff_path.read_text(encoding="utf-8")
    assert "diff --git" in diff_text
    assert "+VALUE = 2" in diff_text

    manifest = _read_manifest(output_dir)
    assert manifest["schema_version"] == "1"
    diff_entry = next(item for item in manifest["artifacts"] if item["kind"] == "git_diff")
    assert diff_entry["relative_path"] == "artifacts/git-diff.patch"
    assert diff_entry["sha256"] == hashlib.sha256(diff_path.read_bytes()).hexdigest()
    assert diff_entry["size_bytes"] == len(diff_path.read_bytes())
    packet_entry = next(item for item in manifest["artifacts"] if item["kind"] == "proof_packet")
    assert packet_entry["relative_path"] == summary["proof_packet_relative_path"]


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
    assert summary["schema_version"] == "2"
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
    assert summary["schema_version"] == "2"
    assert summary["status"] == "failed"
    assert summary["proof_packet_path"] is None
    assert summary["proof_packet_relative_path"] is None
    assert summary["artifact_manifest_path"] is None
    assert summary["diff_artifact_path"] is None
    assert summary["test_command_policy"] == "not_run_by_ci_design"
    assert "simulated review failure" in summary["error"]
