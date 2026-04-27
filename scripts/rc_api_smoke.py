from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def run_smoke(temp_root: Path) -> dict[str, Any]:
    temp_root = temp_root.resolve()
    db_path = temp_root / "proofflow-smoke.db"
    data_dir = temp_root / "data"
    os.environ["PROOFFLOW_DB_PATH"] = str(db_path)
    os.environ["PROOFFLOW_DATA_DIR"] = str(data_dir)

    from fastapi.testclient import TestClient
    from proofflow.main import app

    with TestClient(app) as client:
        health = _require_ok(client.get("/health"), "GET /health")
        _assert_release_identity(health)

        localproof = _run_localproof_action_smoke(client, temp_root)
        agentguard = _run_agentguard_packet_smoke(client, temp_root)

    return {
        "db_path": str(db_path),
        "data_dir": str(data_dir),
        "health": health,
        "localproof": localproof,
        "agentguard": agentguard,
    }


def _run_localproof_action_smoke(client: Any, temp_root: Path) -> dict[str, Any]:
    inbox = temp_root / "localproof" / "inbox"
    target_root = temp_root / "localproof" / "sorted"
    inbox.mkdir(parents=True)
    (inbox / "notes.md").write_text("# RC smoke note\n", encoding="utf-8")
    (inbox / "run.log").write_text("rc smoke log\n", encoding="utf-8")

    scan = _require_ok(
        client.post(
            "/localproof/scan",
            json={"folder_path": str(inbox), "recursive": True, "max_files": 20},
        ),
        "POST /localproof/scan",
    )
    suggest = _require_ok(
        client.post(
            "/localproof/suggest-actions",
            json={"case_id": scan["case_id"], "target_root": str(target_root)},
        ),
        "POST /localproof/suggest-actions",
    )

    actions = suggest["actions"]
    notes_move = _find_move_action(actions, "notes.md")
    notes_mkdir = _find_dependency_action(actions, notes_move)
    log_move = _find_move_action(actions, "run.log")
    log_mkdir = _find_dependency_action(actions, log_move)

    _approve_execute(client, notes_mkdir)
    _approve_execute(client, notes_move)
    _require_ok(client.post(f"/actions/{notes_move['id']}/undo"), "undo notes.md")
    _require_ok(client.post(f"/actions/{notes_mkdir['id']}/undo"), "undo Notes dir")
    if (target_root / "Notes" / "notes.md").exists():
        raise RuntimeError("notes.md destination still exists after undo")
    if (inbox / "notes.md").read_text(encoding="utf-8") != "# RC smoke note\n":
        raise RuntimeError("notes.md was not restored after undo")

    _approve_execute(client, log_mkdir)
    _approve_execute(client, log_move)
    log_destination = Path(log_move["preview"]["to_path"])
    log_destination.write_text("changed after execution\n", encoding="utf-8")
    refused = client.post(f"/actions/{log_move['id']}/undo")
    if refused.status_code != 400:
        raise RuntimeError(f"changed-file undo should return 400, got {refused.status_code}")
    if "undo source changed" not in refused.json().get("detail", ""):
        raise RuntimeError(f"unexpected changed-file undo detail: {refused.text}")

    listed_actions = _require_ok(
        client.get(f"/cases/{scan['case_id']}/actions"),
        "GET /cases/{case_id}/actions",
    )
    if not all(action["metadata"].get("allowed_roots") for action in listed_actions):
        raise RuntimeError("LocalProof actions are missing allowed_roots metadata")

    return {
        "case_id": scan["case_id"],
        "files_seen": scan["files_seen"],
        "actions_created": suggest["actions_created"],
        "changed_file_undo_status": refused.status_code,
    }


def _run_agentguard_packet_smoke(client: Any, temp_root: Path) -> dict[str, Any]:
    if shutil.which("git") is None:
        return {"skipped": True, "reason": "git executable was not found"}

    repo = _init_agentguard_repo(temp_root / "agentguard-repo")
    (repo / "app.py").write_text("VALUE = 2\n", encoding="utf-8")
    (repo / ".env").write_text("PROOFFLOW_SECRET=rc-smoke-secret\n", encoding="utf-8")
    (repo / "local.sqlite").write_bytes(b"SQLite format 3\x00sqlite-secret")
    (repo / "secret.pem").write_text(
        "-----BEGIN PRIVATE KEY-----\npem-secret\n",
        encoding="utf-8",
    )

    review = _require_ok(
        client.post(
            "/agentguard/review",
            json={
                "repo_path": str(repo),
                "include_untracked": True,
                "test_command": f'"{sys.executable}" run_tests.py',
            },
        ),
        "POST /agentguard/review",
    )
    if "app.py" not in review["changed_files"]:
        raise RuntimeError("AgentGuard did not report modified app.py")

    packet = _require_ok(
        client.get(f"/cases/{review['case_id']}/packet"),
        "GET /cases/{case_id}/packet",
    )
    if not packet["claims"]:
        raise RuntimeError("AgentGuard packet has no claims")
    evidence_items = [
        evidence
        for claim in packet["claims"]
        for evidence in claim.get("evidence", [])
    ]
    if not evidence_items:
        raise RuntimeError("AgentGuard packet has no evidence")

    export = _require_ok(
        client.post(
            f"/reports/cases/{review['case_id']}/export",
            json={"format": "markdown"},
        ),
        "POST /reports/cases/{case_id}/export",
    )
    content = export["content"]
    for secret in ("rc-smoke-secret", "sqlite-secret", "pem-secret"):
        if secret in content:
            raise RuntimeError(f"Proof Packet leaked sensitive marker: {secret}")
    if "sensitive_untracked_file" not in content:
        raise RuntimeError("Proof Packet is missing sensitive untracked policy evidence")

    return {
        "case_id": review["case_id"],
        "changed_files": review["changed_files"],
        "claims_created": review["claims_created"],
        "evidence_created": review["evidence_created"],
        "packet_path": export["path"],
    }


def _assert_release_identity(health: dict[str, Any]) -> None:
    expected = {
        "ok": True,
        "service": "proofflow-backend",
        "version": "0.1.0-rc1",
        "release_stage": "rc",
        "release_name": "ProofFlow v0.1.0-rc1",
    }
    for key, value in expected.items():
        if health.get(key) != value:
            raise RuntimeError(f"health {key} mismatch: expected {value!r}, got {health.get(key)!r}")


def _approve_execute(client: Any, action: dict[str, Any]) -> dict[str, Any]:
    _require_ok(client.post(f"/actions/{action['id']}/approve"), f"approve {action['id']}")
    return _require_ok(client.post(f"/actions/{action['id']}/execute"), f"execute {action['id']}")


def _find_move_action(actions: list[dict[str, Any]], file_name: str) -> dict[str, Any]:
    for action in actions:
        if action["kind"] == "move_file" and Path(action["preview"]["from_path"]).name == file_name:
            return action
    raise RuntimeError(f"move_file action not found for {file_name}")


def _find_dependency_action(
    actions: list[dict[str, Any]],
    action: dict[str, Any],
) -> dict[str, Any]:
    dependency_id = action["metadata"].get("depends_on_action_id")
    for candidate in actions:
        if candidate["id"] == dependency_id:
            return candidate
    raise RuntimeError(f"dependency action not found for {action['id']}")


def _require_ok(response: Any, label: str) -> dict[str, Any]:
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"{label} failed with {response.status_code}: {response.text}")
    return response.json()


def _init_agentguard_repo(repo: Path) -> Path:
    repo.mkdir(parents=True)
    (repo / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (repo / "run_tests.py").write_text(
        "print('rc smoke tests passed')\nraise SystemExit(0)\n",
        encoding="utf-8",
    )
    _git(repo, "init")
    _git(repo, "config", "user.email", "prooflow-smoke@example.test")
    _git(repo, "config", "user.name", "ProofFlow Smoke")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "baseline")
    return repo


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


def _remove_tree(path: Path) -> None:
    def retry_readonly(function: Any, item: str, exc_info: Any) -> None:
        try:
            os.chmod(item, stat.S_IWRITE)
            function(item)
        except OSError:
            raise exc_info[1]

    shutil.rmtree(path, onerror=retry_readonly)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the v0.1.0-rc1 API dogfood smoke check with temp DB/data."
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=None,
        help="Optional smoke output directory. Defaults to a temporary directory.",
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove the generated temp directory after a successful run.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    temp_root = (args.work_dir or Path(tempfile.mkdtemp(prefix="proofflow-rc-api-smoke-"))).resolve()
    temp_root.mkdir(parents=True, exist_ok=True)
    should_cleanup = args.work_dir is None and args.cleanup
    smoke_passed = False
    try:
        result = run_smoke(temp_root)
        smoke_passed = True
        print("ProofFlow v0.1.0-rc1 API smoke passed.")
        print(f"Temp root: {temp_root}")
        print(f"DB path: {result['db_path']}")
        print(f"Data dir: {result['data_dir']}")
        print(f"LocalProof case: {result['localproof']['case_id']}")
        print(f"LocalProof actions created: {result['localproof']['actions_created']}")
        if result["agentguard"].get("skipped"):
            print(f"AgentGuard skipped: {result['agentguard']['reason']}")
        else:
            print(f"AgentGuard case: {result['agentguard']['case_id']}")
            print(f"Proof Packet: {result['agentguard']['packet_path']}")
        if should_cleanup:
            print("Temp root will be removed after this run.")
        else:
            print("Temp root retained for inspection. Re-run with --cleanup to remove it automatically.")
        return 0
    finally:
        if should_cleanup and smoke_passed:
            _remove_tree(temp_root)


if __name__ == "__main__":
    raise SystemExit(main())
