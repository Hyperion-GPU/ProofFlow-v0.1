from pathlib import Path
import json
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from proofflow.config import get_db_path
from proofflow.db import connect
from proofflow.main import app


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(tmp_path / "ledger.db"))
    monkeypatch.setenv("PROOFFLOW_DATA_DIR", str(tmp_path / "data"))
    return TestClient(app)


def _start_ledger(client: TestClient, tmp_path: Path, **overrides) -> dict:
    payload = {
        "objective": "Implement ledger feature",
        "repo_path": str(tmp_path),
        "allowed_scope": [],
        "forbidden_actions": [],
        "required_tests": [],
        "done_criteria": ["packet exports"],
        "evidence_requirements": [],
    }
    payload.update(overrides)
    response = client.post("/ledger/start", json=payload)
    assert response.status_code == 200
    return response.json()


def _require_git() -> None:
    if shutil.which("git") is None:
        pytest.skip("git executable is not available")


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _init_repo(repo: Path) -> Path:
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "ledger@example.test")
    _git(repo, "config", "user.name", "Ledger Test")
    (repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")
    return repo


def _artifact_chunks(artifact_id: str) -> str:
    with connect(get_db_path()) as connection:
        rows = connection.execute(
            """
            SELECT content
            FROM artifact_text_chunks
            WHERE artifact_id = ?
            ORDER BY chunk_index ASC
            """,
            (artifact_id,),
        ).fetchall()
    return "\n".join(row["content"] for row in rows)


def test_ledger_start_events_finish_and_export_packet(monkeypatch, tmp_path):
    _require_git()
    repo = _init_repo(tmp_path / "repo")

    with _client(monkeypatch, tmp_path) as client:
        started = _start_ledger(client, tmp_path, repo_path=str(repo))
        case_id = started["case_id"]

        first = client.post(
            f"/ledger/cases/{case_id}/events",
            json={
                "event_type": "command",
                "summary": "Ran targeted tests",
                "content": "python -m pytest backend/tests/test_agent_work_ledger.py",
                "metadata": {"command": "python -m pytest"},
            },
        )
        second = client.post(
            f"/ledger/cases/{case_id}/events",
            json={
                "event_type": "note",
                "summary": "Reviewed packet output",
                "content": "Packet contained contract and timeline.",
                "metadata": {},
            },
        )
        snapshot = client.post(
            f"/ledger/cases/{case_id}/snapshots",
            json={"repo_path": str(repo), "phase": "final"},
        )
        finished = client.post(
            f"/ledger/cases/{case_id}/finish",
            json={"summary": "Ledger foundation complete"},
        )
        exported = client.post(f"/reports/cases/{case_id}/export", json={"format": "markdown"})

    assert first.status_code == 200
    assert first.json()["sequence"] == 1
    assert second.status_code == 200
    assert second.json()["sequence"] == 2
    assert snapshot.status_code == 200
    assert finished.status_code == 200
    assert finished.json()["status"] == "finished"

    with connect(get_db_path()) as connection:
        case = connection.execute(
            "SELECT case_type, status, metadata_json FROM cases WHERE id = ?",
            (case_id,),
        ).fetchone()
        artifact_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM case_artifacts
            JOIN artifacts ON artifacts.id = case_artifacts.artifact_id
            WHERE case_artifacts.case_id = ? AND artifacts.artifact_type = 'log'
            """,
            (case_id,),
        ).fetchone()[0]

    assert case["case_type"] == "agent_work_ledger"
    assert case["status"] == "active"
    assert json.loads(case["metadata_json"])["status"] == "finished"
    assert artifact_count == 2
    assert "Ran targeted tests" in _artifact_chunks(first.json()["artifact_id"])
    assert exported.status_code == 200
    content = exported.json()["content"]
    assert "## Work Contract" in content
    assert "## Ledger Timeline" in content
    assert "Ran targeted tests" in content


def test_ledger_finish_requires_final_snapshot(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        case_id = _start_ledger(client, tmp_path)["case_id"]
        response = client.post(
            f"/ledger/cases/{case_id}/finish",
            json={"summary": "No snapshot yet"},
        )

    assert response.status_code == 400
    assert "final snapshot" in response.json()["detail"]


def test_ledger_capture_snapshot_records_diff_and_packet_metadata(monkeypatch, tmp_path):
    _require_git()
    repo = _init_repo(tmp_path / "repo")
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    with _client(monkeypatch, tmp_path) as client:
        case_id = _start_ledger(
            client,
            tmp_path,
            repo_path=str(repo),
            allowed_scope=["app.py"],
            evidence_requirements=["git_diff"],
        )["case_id"]
        snapshot = client.post(
            f"/ledger/cases/{case_id}/snapshots",
            json={
                "repo_path": str(repo),
                "phase": "final",
                "base_ref": "HEAD",
                "include_untracked": True,
            },
        )
        exported = client.post(f"/reports/cases/{case_id}/export", json={"format": "markdown"})

    assert snapshot.status_code == 200
    payload = snapshot.json()
    assert payload["phase"] == "final"
    assert payload["changed_files"] == ["app.py"]
    assert len(payload["head_sha"]) >= 7
    assert len(payload["diff_sha256"]) == 64
    assert "VALUE = 2" in _artifact_chunks(payload["artifact_id"])

    with connect(get_db_path()) as connection:
        row = connection.execute(
            "SELECT metadata_json FROM artifacts WHERE id = ?",
            (payload["artifact_id"],),
        ).fetchone()
    metadata = json.loads(row["metadata_json"])
    assert metadata["phase"] == "final"
    assert metadata["changed_file_count"] == 1
    assert metadata["diff_sha256"] == payload["diff_sha256"]

    assert "## Snapshots" in exported.json()["content"]
    assert payload["diff_sha256"] in exported.json()["content"]


def test_ledger_records_evidence_and_requires_claim_bindings(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        case_id = _start_ledger(client, tmp_path)["case_id"]
        evidence = client.post(
            f"/ledger/cases/{case_id}/evidence",
            json={
                "evidence_type": "test_output",
                "content": "python -m pytest passed",
                "source_ref": "pytest",
                "metadata": {"command": "python -m pytest"},
            },
        )
        claim = client.post(
            f"/ledger/cases/{case_id}/claims",
            json={
                "claim_text": "Tests passed",
                "severity": "info",
                "evidence_ids": [evidence.json()["evidence_id"]],
            },
        )
        empty_claim = client.post(
            f"/ledger/cases/{case_id}/claims",
            json={
                "claim_text": "No evidence claim",
                "severity": "medium",
                "evidence_ids": [],
            },
        )
        exported = client.post(f"/reports/cases/{case_id}/export", json={"format": "markdown"})

    assert evidence.status_code == 200
    assert claim.status_code == 200
    assert empty_claim.status_code == 422

    with connect(get_db_path()) as connection:
        row = connection.execute(
            "SELECT claim_id FROM evidence WHERE id = ?",
            (evidence.json()["evidence_id"],),
        ).fetchone()
    assert row["claim_id"] == claim.json()["claim_id"]
    assert "Tests passed" in exported.json()["content"]
    assert "python -m pytest passed" in exported.json()["content"]


def test_ledger_evaluator_reports_missing_tests(monkeypatch, tmp_path):
    with _client(monkeypatch, tmp_path) as client:
        case_id = _start_ledger(
            client,
            tmp_path,
            required_tests=["python -m pytest"],
        )["case_id"]
        response = client.post(f"/ledger/cases/{case_id}/evaluate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "needs_tests"
    assert "needs_tests" in payload["failed"]


def test_ledger_evaluator_reports_scope_violation(monkeypatch, tmp_path):
    _require_git()
    repo = _init_repo(tmp_path / "repo")
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    with _client(monkeypatch, tmp_path) as client:
        case_id = _start_ledger(
            client,
            tmp_path,
            repo_path=str(repo),
            allowed_scope=["src/"],
        )["case_id"]
        client.post(
            f"/ledger/cases/{case_id}/snapshots",
            json={"repo_path": str(repo), "phase": "final"},
        )
        response = client.post(f"/ledger/cases/{case_id}/evaluate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "scope_violation"
    assert payload["scope_violations"] == ["app.py"]


def test_ledger_evaluator_preserves_dotfile_scope_paths(monkeypatch, tmp_path):
    _require_git()
    repo = _init_repo(tmp_path / "repo")
    (repo / ".codex").mkdir()
    (repo / ".codex" / "config.toml").write_text("mode = 'test'\n", encoding="utf-8")

    with _client(monkeypatch, tmp_path) as client:
        case_id = _start_ledger(
            client,
            tmp_path,
            repo_path=str(repo),
            allowed_scope=[".codex"],
        )["case_id"]
        client.post(
            f"/ledger/cases/{case_id}/snapshots",
            json={"repo_path": str(repo), "phase": "final"},
        )
        response = client.post(f"/ledger/cases/{case_id}/evaluate")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready_for_review"
    assert payload["scope_violations"] == []


def test_ledger_finish_after_failed_evaluation_marks_finished_with_risks(monkeypatch, tmp_path):
    _require_git()
    repo = _init_repo(tmp_path / "repo")
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    with _client(monkeypatch, tmp_path) as client:
        case_id = _start_ledger(
            client,
            tmp_path,
            repo_path=str(repo),
            allowed_scope=["src/"],
        )["case_id"]
        client.post(
            f"/ledger/cases/{case_id}/snapshots",
            json={"repo_path": str(repo), "phase": "final"},
        )
        evaluation = client.post(f"/ledger/cases/{case_id}/evaluate")
        finished = client.post(
            f"/ledger/cases/{case_id}/finish",
            json={"summary": "Finished after scope violation"},
        )

    assert evaluation.status_code == 200
    assert evaluation.json()["status"] == "scope_violation"
    assert finished.status_code == 200
    assert finished.json()["status"] == "finished_with_risks"
    assert finished.json()["metadata"]["latest_evaluation_status"] == "scope_violation"


def test_ledger_evaluator_reports_ready_for_review(monkeypatch, tmp_path):
    _require_git()
    repo = _init_repo(tmp_path / "repo")
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

    with _client(monkeypatch, tmp_path) as client:
        case_id = _start_ledger(
            client,
            tmp_path,
            repo_path=str(repo),
            allowed_scope=["app.py"],
            required_tests=["python -m pytest"],
            evidence_requirements=["git_diff", "test_output"],
        )["case_id"]
        client.post(
            f"/ledger/cases/{case_id}/snapshots",
            json={"repo_path": str(repo), "phase": "final"},
        )
        client.post(
            f"/ledger/cases/{case_id}/evidence",
            json={
                "evidence_type": "test_output",
                "content": "python -m pytest passed",
                "metadata": {"command": "python -m pytest"},
            },
        )
        response = client.post(f"/ledger/cases/{case_id}/evaluate")
        exported = client.post(f"/reports/cases/{case_id}/export", json={"format": "markdown"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready_for_review"
    assert payload["failed"] == []
    content = exported.json()["content"]
    assert "## Done Criteria Evaluation" in content
    assert "ready_for_review" in content
