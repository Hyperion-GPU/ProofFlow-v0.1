from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import stat
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
REPO_LIVE_DATA_ROOT = BACKEND_ROOT / "data"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def run_smoke(temp_root: Path) -> dict[str, Any]:
    temp_root = temp_root.resolve(strict=False)
    db_path = temp_root / "proofflow-backup-restore-smoke.db"
    data_dir = temp_root / "data"
    backup_root = temp_root / "backups"
    restore_root = temp_root / "restore"
    target_db_path = restore_root / "proofflow-restored.db"
    target_data_dir = restore_root / "data"

    _assert_isolated_paths(db_path, data_dir, backup_root, restore_root)
    os.environ["PROOFFLOW_DB_PATH"] = str(db_path)
    os.environ["PROOFFLOW_DATA_DIR"] = str(data_dir)

    from fastapi.testclient import TestClient
    from proofflow.main import app

    with TestClient(app) as client:
        health = _require_ok(client.get("/health"), "GET /health")
        _seed_managed_files(data_dir)

        backup_preview = _require_ok(
            client.post(
                "/backups/preview",
                json={
                    "backup_root": str(backup_root),
                    "include_data_dir": True,
                    "include_proof_packets": True,
                },
            ),
            "POST /backups/preview",
        )
        if backup_root.exists():
            raise RuntimeError("backup preview created the backup root")

        backup = _require_ok(
            client.post(
                "/backups",
                json={"backup_root": str(backup_root), "label": "api-smoke"},
            ),
            "POST /backups",
        )
        backup_id = backup["backup_id"]
        backups_list = _require_ok(client.get("/backups"), "GET /backups")
        backup_detail = _require_ok(client.get(f"/backups/{backup_id}"), "GET /backups/{backup_id}")
        verification = _require_ok(
            client.post(f"/backups/{backup_id}/verify", json={}),
            "POST /backups/{backup_id}/verify",
        )
        if verification["status"] != "verified":
            raise RuntimeError(f"backup verification failed: {verification}")

        restore_preview = _require_ok(
            client.post(
                "/restore/preview",
                json={
                    "backup_id": backup_id,
                    "target_db_path": str(target_db_path),
                    "target_data_dir": str(target_data_dir),
                },
            ),
            "POST /restore/preview",
        )
        if target_db_path.exists() or target_data_dir.exists():
            raise RuntimeError("restore preview created target filesystem paths")

        live_sentinel = _create_live_sentinel(client, data_dir)
        restored = _require_ok(
            client.post(
                "/restore/to-new-location",
                json={
                    "backup_id": backup_id,
                    "target_db_path": str(target_db_path),
                    "target_data_dir": str(target_data_dir),
                    "accepted_preview_id": restore_preview["restore_preview_id"],
                },
            ),
            "POST /restore/to-new-location",
        )

    _assert_restored_database(target_db_path)
    _assert_restored_files(target_data_dir)
    _assert_live_state_not_overwritten(db_path, live_sentinel)

    return {
        "temp_root": str(temp_root),
        "db_path": str(db_path),
        "data_dir": str(data_dir),
        "backup_root": str(backup_root),
        "backup_id": backup_id,
        "backup_preview_files": len(backup_preview["planned_files"]),
        "backups_listed": len(backups_list["backups"]),
        "backup_detail_status": backup_detail["verification"]["status"],
        "verification_status": verification["status"],
        "restore_preview_id": restore_preview["restore_preview_id"],
        "restore_planned_writes": len(restore_preview["planned_writes"]),
        "restore_status": restored["status"],
        "restored_files": restored["restored_files"],
        "target_db_path": str(target_db_path),
        "target_data_dir": str(target_data_dir),
        "health": health,
    }


def _seed_managed_files(data_dir: Path) -> None:
    notes_dir = data_dir / "notes"
    packets_dir = data_dir / "proof_packets"
    notes_dir.mkdir(parents=True, exist_ok=True)
    packets_dir.mkdir(parents=True, exist_ok=True)
    (notes_dir / "backup-restore-smoke.txt").write_text(
        "managed data for backup restore smoke\n",
        encoding="utf-8",
    )
    (packets_dir / "backup-restore-smoke.md").write_text(
        "# Backup Restore Smoke\n",
        encoding="utf-8",
    )


def _create_live_sentinel(client: Any, data_dir: Path) -> dict[str, str]:
    response = _require_ok(
        client.post(
            "/cases",
            json={
                "title": "Backup restore smoke live sentinel",
                "kind": "local_proof",
                "summary": "Created after backup snapshot to detect accidental live DB overwrite.",
            },
        ),
        "POST /cases live sentinel",
    )
    data_sentinel_path = data_dir / "live-sentinel-after-preview.txt"
    data_sentinel_content = "live data sentinel after restore preview\n"
    data_sentinel_path.write_text(data_sentinel_content, encoding="utf-8")
    return {
        "case_id": response["id"],
        "data_path": str(data_sentinel_path),
        "data_content": data_sentinel_content,
    }


def _assert_restored_database(target_db_path: Path) -> None:
    if not target_db_path.exists():
        raise RuntimeError(f"restored SQLite DB is missing: {target_db_path}")
    connection = sqlite3.connect(target_db_path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    finally:
        connection.close()
    required_tables = {"cases", "artifacts", "evidence", "backups", "restore_previews"}
    missing = sorted(required_tables - tables)
    if missing:
        raise RuntimeError(f"restored SQLite DB is missing tables: {missing}")


def _assert_restored_files(target_data_dir: Path) -> None:
    managed_file = target_data_dir / "notes" / "backup-restore-smoke.txt"
    proof_packet = target_data_dir / "proof_packets" / "backup-restore-smoke.md"
    if managed_file.read_text(encoding="utf-8") != "managed data for backup restore smoke\n":
        raise RuntimeError(f"restored managed data file mismatch: {managed_file}")
    if proof_packet.read_text(encoding="utf-8") != "# Backup Restore Smoke\n":
        raise RuntimeError(f"restored proof packet mismatch: {proof_packet}")


def _assert_live_state_not_overwritten(db_path: Path, sentinel: dict[str, str]) -> None:
    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute(
            "SELECT id FROM cases WHERE id = ?",
            (sentinel["case_id"],),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise RuntimeError("live DB sentinel case disappeared after restore")

    data_path = Path(sentinel["data_path"])
    if data_path.read_text(encoding="utf-8") != sentinel["data_content"]:
        raise RuntimeError("live data sentinel changed after restore")


def _assert_isolated_paths(*paths: Path) -> None:
    temp_root = Path(tempfile.gettempdir()).resolve(strict=False)
    repo_live_root = REPO_LIVE_DATA_ROOT.resolve(strict=False)
    for path in paths:
        resolved = path.resolve(strict=False)
        if _is_at_or_under(resolved, repo_live_root):
            raise RuntimeError(f"refusing to use repo live data path: {resolved}")
        if not _is_at_or_under(resolved, temp_root):
            raise RuntimeError(f"refusing to use non-temp smoke path: {resolved}")


def _is_at_or_under(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _require_ok(response: Any, label: str) -> dict[str, Any]:
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(f"{label} failed with {response.status_code}: {response.text}")
    return response.json()


def _remove_tree(path: Path) -> None:
    def retry_readonly(function: Any, item: str, exc_info: Any) -> None:
        last_error = exc_info[1]
        for _attempt in range(10):
            try:
                os.chmod(item, stat.S_IWRITE)
                function(item)
                return
            except PermissionError as error:
                last_error = error
                time.sleep(0.2)
            except OSError as error:
                last_error = error
                break
        raise last_error

    shutil.rmtree(path, onerror=retry_readonly)


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an isolated managed backup/restore backend API smoke check."
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove the generated temp directory after a successful run.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    temp_root = Path(tempfile.mkdtemp(prefix="proofflow-backup-restore-smoke-")).resolve()
    smoke_passed = False
    try:
        result = run_smoke(temp_root)
        smoke_passed = True
        print("ProofFlow backup/restore API smoke passed.")
        print(f"Temp root: {result['temp_root']}")
        print(f"Live DB path: {result['db_path']}")
        print(f"Live data dir: {result['data_dir']}")
        print(f"Backup root: {result['backup_root']}")
        print(f"Backup ID: {result['backup_id']}")
        print(f"Backup preview files: {result['backup_preview_files']}")
        print(f"Restore preview ID: {result['restore_preview_id']}")
        print(f"Restore planned writes: {result['restore_planned_writes']}")
        print(f"Restored files: {result['restored_files']}")
        print(f"Restored DB path: {result['target_db_path']}")
        print(f"Restored data dir: {result['target_data_dir']}")
        if args.cleanup:
            print("Temp root will be removed after this run.")
        else:
            print("Temp root retained for inspection. Re-run with --cleanup to remove it automatically.")
        return 0
    except Exception as error:
        print(f"ProofFlow backup/restore API smoke failed: {error}", file=sys.stderr)
        print(f"Temp root retained for failure evidence: {temp_root}", file=sys.stderr)
        return 1
    finally:
        if args.cleanup and smoke_passed:
            _remove_tree(temp_root)


if __name__ == "__main__":
    raise SystemExit(main())
