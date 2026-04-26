from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile

import pytest
from fastapi.testclient import TestClient

from proofflow.config import get_db_path
from proofflow.db import connect
from proofflow.main import app


def _require_git() -> None:
    if shutil.which("git") is None:
        pytest.skip("git executable is not available")


def _client(monkeypatch, temp_root: Path) -> TestClient:
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(temp_root / "agentguard.db"))
    monkeypatch.setenv("PROOFFLOW_DATA_DIR", str(temp_root / "data"))
    return TestClient(app)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


def _init_repo(repo: Path) -> Path:
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "agentguard@example.test")
    _git(repo, "config", "user.name", "AgentGuard Test")
    (repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")
    return repo


def _git_diff_chunk_text(case_id: str) -> str:
    with connect(get_db_path()) as connection:
        rows = connection.execute(
            """
            SELECT artifact_text_chunks.content
            FROM artifact_text_chunks
            JOIN artifacts ON artifacts.id = artifact_text_chunks.artifact_id
            JOIN case_artifacts ON case_artifacts.artifact_id = artifacts.id
            WHERE case_artifacts.case_id = ?
              AND artifacts.artifact_type = 'git_diff'
            ORDER BY artifact_text_chunks.chunk_index ASC
            """,
            (case_id,),
        ).fetchall()
    return "\n".join(row["content"] for row in rows)


def _git_diff_artifact_metadata(case_id: str) -> dict:
    with connect(get_db_path()) as connection:
        row = connection.execute(
            """
            SELECT artifacts.metadata_json
            FROM artifacts
            JOIN case_artifacts ON case_artifacts.artifact_id = artifacts.id
            WHERE case_artifacts.case_id = ?
              AND artifacts.artifact_type = 'git_diff'
            """,
            (case_id,),
        ).fetchone()
    assert row is not None
    return json.loads(row["metadata_json"])


def _claim_evidence_text(case_id: str) -> str:
    with connect(get_db_path()) as connection:
        rows = connection.execute(
            """
            SELECT claims.claim_text, evidence.content
            FROM claims
            JOIN evidence ON evidence.claim_id = claims.id
            WHERE claims.case_id = ?
            ORDER BY claims.created_at ASC, claims.id ASC
            """,
            (case_id,),
        ).fetchall()
    return "\n".join(f"{row['claim_text']}\n{row['content']}" for row in rows)


def test_agentguard_review_records_modified_file_claims_and_evidence(monkeypatch):
    _require_git()
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        repo = _init_repo(temp_root / "repo")
        (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")

        with _client(monkeypatch, temp_root) as client:
            response = client.post("/agentguard/review", json={"repo_path": str(repo)})

        assert response.status_code == 200
        payload = response.json()
        assert payload["risk_level"] == "info"
        assert payload["changed_files"] == ["app.py"]
        assert payload["claims_created"] >= 1
        assert payload["evidence_created"] == payload["claims_created"]
        assert payload["artifacts"][0]["kind"] == "git_diff"

        with connect(get_db_path()) as connection:
            case = connection.execute(
                "SELECT case_type, metadata_json FROM cases WHERE id = ?",
                (payload["case_id"],),
            ).fetchone()
            chunk = connection.execute(
                """
                SELECT artifact_text_chunks.content
                FROM artifact_text_chunks
                JOIN artifacts ON artifacts.id = artifact_text_chunks.artifact_id
                WHERE artifacts.artifact_type = 'git_diff'
                """
            ).fetchone()
            evidence_rows = connection.execute(
                """
                SELECT evidence.content, claims.metadata_json
                FROM evidence
                JOIN claims ON claims.id = evidence.claim_id
                WHERE evidence.case_id = ?
                """,
                (payload["case_id"],),
            ).fetchall()

        assert case["case_type"] == "code_review"
        assert json.loads(case["metadata_json"])["risk_level"] == "info"
        assert "app.py" in chunk["content"]
        assert any("app.py" in row["content"] for row in evidence_rows)
        assert all("severity" in json.loads(row["metadata_json"]) for row in evidence_rows)


def test_agentguard_review_records_failing_test_as_high_risk(monkeypatch):
    _require_git()
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        repo = _init_repo(temp_root / "repo")
        (repo / "fail_test.py").write_text(
            "import sys\nprint('failing test')\nsys.stderr.write('boom\\n')\nsys.exit(1)\n",
            encoding="utf-8",
        )
        _git(repo, "add", ".")
        _git(repo, "commit", "-m", "add failing command")
        command = f'"{sys.executable}" fail_test.py'

        with _client(monkeypatch, temp_root) as client:
            response = client.post(
                "/agentguard/review",
                json={
                    "repo_path": str(repo),
                    "include_untracked": False,
                    "test_command": command,
                },
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["risk_level"] == "high"
        assert any(artifact["kind"] == "test_output" for artifact in payload["artifacts"])

        with connect(get_db_path()) as connection:
            high_claim = connection.execute(
                """
                SELECT claims.claim_text, claims.metadata_json, evidence.content
                FROM claims
                JOIN evidence ON evidence.claim_id = claims.id
                WHERE claims.case_id = ? AND evidence.evidence_type = 'test_output'
                """,
                (payload["case_id"],),
            ).fetchone()
            run = connection.execute(
                "SELECT status, metadata_json FROM runs WHERE id = ?",
                (payload["run_id"],),
            ).fetchone()
            test_output_chunk = connection.execute(
                """
                SELECT artifact_text_chunks.content
                FROM artifact_text_chunks
                JOIN artifacts ON artifacts.id = artifact_text_chunks.artifact_id
                WHERE artifacts.artifact_type = 'test_output'
                """
            ).fetchone()

        assert high_claim is not None
        assert json.loads(high_claim["metadata_json"])["severity"] == "high"
        assert "failed" in high_claim["claim_text"].lower()
        assert run["status"] == "failed"
        assert json.loads(run["metadata_json"])["test_status"] == "failed"
        assert "failing test" in test_output_chunk["content"]
        assert "boom" in test_output_chunk["content"]


def test_agentguard_review_honors_include_untracked(monkeypatch):
    _require_git()
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        repo = _init_repo(temp_root / "repo")
        (repo / "draft.txt").write_text("draft content\n", encoding="utf-8")

        with _client(monkeypatch, temp_root) as client:
            included = client.post(
                "/agentguard/review",
                json={"repo_path": str(repo), "include_untracked": True},
            )
            excluded = client.post(
                "/agentguard/review",
                json={"repo_path": str(repo), "include_untracked": False},
            )

        assert included.status_code == 200
        assert excluded.status_code == 200
        assert "draft.txt" in included.json()["changed_files"]
        assert "draft.txt" not in excluded.json()["changed_files"]

        with connect(get_db_path()) as connection:
            included_chunk = connection.execute(
                """
                SELECT artifact_text_chunks.content
                FROM artifact_text_chunks
                JOIN artifacts ON artifacts.id = artifact_text_chunks.artifact_id
                WHERE artifacts.artifact_type = 'git_diff'
                  AND artifacts.metadata_json LIKE '%draft.txt%'
                ORDER BY artifacts.created_at ASC
                """
            ).fetchone()

        assert included_chunk is not None
        assert "draft content" in included_chunk["content"]


def test_agentguard_review_omits_sensitive_untracked_file_contents(monkeypatch):
    _require_git()
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        repo = _init_repo(temp_root / "repo")
        (repo / ".env").write_text("PROOFFLOW_SECRET=env-secret\n", encoding="utf-8")
        (repo / "secret.pem").write_text("-----BEGIN PRIVATE KEY-----\npem-secret\n", encoding="utf-8")
        (repo / "local.sqlite").write_bytes(b"SQLite format 3\x00sqlite-secret")

        with _client(monkeypatch, temp_root) as client:
            response = client.post(
                "/agentguard/review",
                json={"repo_path": str(repo), "include_untracked": True},
            )
            payload = response.json()
            report_response = client.post(
                f"/reports/cases/{payload['case_id']}/export",
                json={"format": "markdown"},
            )

        assert response.status_code == 200
        assert report_response.status_code == 200
        assert {".env", "secret.pem", "local.sqlite"}.issubset(payload["changed_files"])

        chunk_text = _git_diff_chunk_text(payload["case_id"])
        evidence_text = _claim_evidence_text(payload["case_id"])
        report_text = report_response.json()["content"]
        combined_safe_text = "\n".join([chunk_text, evidence_text, report_text])

        assert "env-secret" not in combined_safe_text
        assert "pem-secret" not in combined_safe_text
        assert "sqlite-secret" not in combined_safe_text
        assert "sensitive_untracked_file" in evidence_text

        metadata = _git_diff_artifact_metadata(payload["case_id"])
        notes = metadata["untracked_policy_notes"]
        assert {item["path"] for item in notes} == {".env", "secret.pem", "local.sqlite"}
        assert all(item["reason"] == "sensitive_untracked_file" for item in notes)


def test_agentguard_review_omits_oversized_untracked_text_content(monkeypatch):
    _require_git()
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        repo = _init_repo(temp_root / "repo")
        large_marker = "large-file-secret-marker"
        large_content = large_marker + "\n" + ("x" * (262144 + 100))
        large_path = repo / "large.txt"
        large_path.write_text(large_content, encoding="utf-8")
        large_size = large_path.stat().st_size

        with _client(monkeypatch, temp_root) as client:
            response = client.post(
                "/agentguard/review",
                json={"repo_path": str(repo), "include_untracked": True},
            )

        assert response.status_code == 200
        payload = response.json()
        assert "large.txt" in payload["changed_files"]

        chunk_text = _git_diff_chunk_text(payload["case_id"])
        evidence_text = _claim_evidence_text(payload["case_id"])

        assert large_marker not in chunk_text
        assert "[ProofFlow omitted untracked file content: file exceeds 262144 bytes]" in chunk_text
        assert "untracked_file_exceeds_diff_cap" in evidence_text
        assert "cap_bytes=262144" in evidence_text

        metadata = _git_diff_artifact_metadata(payload["case_id"])
        notes = metadata["untracked_policy_notes"]
        assert notes == [
            {
                "path": "large.txt",
                "reason": "untracked_file_exceeds_diff_cap",
                "truncated": True,
                "size_bytes": large_size,
                "cap_bytes": 262144,
            }
        ]
