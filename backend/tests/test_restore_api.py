from pathlib import Path

from fastapi.testclient import TestClient

from proofflow.main import app


def _client(monkeypatch, tmp_path: Path) -> tuple[TestClient, Path, Path, Path]:
    data_dir = tmp_path / "data"
    db_path = data_dir / "proofflow.db"
    backup_root = tmp_path / "backups"
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(db_path))
    monkeypatch.setenv("PROOFFLOW_DATA_DIR", str(data_dir))
    return TestClient(app), db_path, data_dir, backup_root


def _seed_managed_files(data_dir: Path) -> None:
    (data_dir / "proof_packets").mkdir(parents=True, exist_ok=True)
    (data_dir / "input.txt").write_text("managed data", encoding="utf-8")
    (data_dir / "proof_packets" / "packet.md").write_text("packet", encoding="utf-8")


def _create_verified_backup(client: TestClient, backup_root: Path) -> str:
    created = client.post("/backups", json={"backup_root": str(backup_root)}).json()
    verified = client.post(f"/backups/{created['backup_id']}/verify", json={}).json()
    assert verified["status"] == "verified"
    return created["backup_id"]


def test_post_restore_preview_rejects_unknown_and_unverified_backup(monkeypatch, tmp_path):
    client, _db_path, data_dir, backup_root = _client(monkeypatch, tmp_path)
    target_db_path = tmp_path / "restore" / "proofflow.db"
    target_data_dir = tmp_path / "restore" / "data"
    with client as active_client:
        unknown = active_client.post(
            "/restore/preview",
            json={
                "backup_id": "missing",
                "target_db_path": str(target_db_path),
                "target_data_dir": str(target_data_dir),
            },
        )
        assert unknown.status_code == 404

        _seed_managed_files(data_dir)
        created = active_client.post("/backups", json={"backup_root": str(backup_root)}).json()
        unverified = active_client.post(
            "/restore/preview",
            json={
                "backup_id": created["backup_id"],
                "target_db_path": str(target_db_path),
                "target_data_dir": str(target_data_dir),
            },
        )
        assert unverified.status_code == 400


def test_post_restore_preview_and_to_new_location_happy_path(monkeypatch, tmp_path):
    client, _db_path, data_dir, backup_root = _client(monkeypatch, tmp_path)
    target_db_path = tmp_path / "restore" / "proofflow.db"
    target_data_dir = tmp_path / "restore" / "data"
    with client as active_client:
        _seed_managed_files(data_dir)
        backup_id = _create_verified_backup(active_client, backup_root)
        preview_response = active_client.post(
            "/restore/preview",
            json={
                "backup_id": backup_id,
                "target_db_path": str(target_db_path),
                "target_data_dir": str(target_data_dir),
            },
        )
        assert preview_response.status_code == 200
        preview = preview_response.json()
        assert preview["restore_preview_id"]
        assert preview["plan_hash"]
        assert {write["archive_relative_path"] for write in preview["planned_writes"]} >= {
            "db/proofflow.db",
            "data/input.txt",
            "proof_packets/packet.md",
        }

        restore_response = active_client.post(
            "/restore/to-new-location",
            json={
                "backup_id": backup_id,
                "target_db_path": str(target_db_path),
                "target_data_dir": str(target_data_dir),
                "accepted_preview_id": preview["restore_preview_id"],
            },
        )
        assert restore_response.status_code == 200
        restored = restore_response.json()
        assert restored["status"] == "restored_to_new_location"
        assert target_db_path.exists()
        assert (target_data_dir / "input.txt").read_text(encoding="utf-8") == "managed data"
        assert (target_data_dir / "proof_packets" / "packet.md").read_text(encoding="utf-8") == "packet"


def test_post_restore_preview_rejects_unsafe_parent_path(monkeypatch, tmp_path):
    client, _db_path, data_dir, backup_root = _client(monkeypatch, tmp_path)
    blocking_parent = tmp_path / "not-a-directory"
    blocking_parent.write_text("file", encoding="utf-8")
    target_data_dir = tmp_path / "restore" / "data"
    with client as active_client:
        _seed_managed_files(data_dir)
        backup_id = _create_verified_backup(active_client, backup_root)
        response = active_client.post(
            "/restore/preview",
            json={
                "backup_id": backup_id,
                "target_db_path": str(blocking_parent / "proofflow.db"),
                "target_data_dir": str(target_data_dir),
            },
        )

        assert response.status_code == 400
        assert "parent is not a directory" in response.json()["detail"]


def test_post_restore_to_new_location_rejects_missing_preview_and_no_live_endpoints(
    monkeypatch,
    tmp_path,
):
    client, _db_path, data_dir, backup_root = _client(monkeypatch, tmp_path)
    target_db_path = tmp_path / "restore" / "proofflow.db"
    target_data_dir = tmp_path / "restore" / "data"
    with client as active_client:
        _seed_managed_files(data_dir)
        backup_id = _create_verified_backup(active_client, backup_root)

        missing_preview = active_client.post(
            "/restore/to-new-location",
            json={
                "backup_id": backup_id,
                "target_db_path": str(target_db_path),
                "target_data_dir": str(target_data_dir),
            },
        )
        assert missing_preview.status_code == 422

        unknown_preview = active_client.post(
            "/restore/to-new-location",
            json={
                "backup_id": backup_id,
                "target_db_path": str(target_db_path),
                "target_data_dir": str(target_data_dir),
                "accepted_preview_id": "missing",
            },
        )
        assert unknown_preview.status_code == 404
        assert active_client.post("/restore/live", json={}).status_code == 404
        assert active_client.post("/restore/apply", json={}).status_code == 404
        assert active_client.post("/restore/current", json={}).status_code == 404
        assert active_client.delete(f"/backups/{backup_id}").status_code == 405
