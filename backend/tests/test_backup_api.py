import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from proofflow.db import connect
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


def _count_backups() -> int:
    with connect() as connection:
        return connection.execute("SELECT COUNT(*) AS count FROM backups").fetchone()["count"]


def _rewrite_zip_member(archive_path: Path, target: str, content: bytes) -> None:
    with zipfile.ZipFile(archive_path, "r") as archive:
        entries = {
            name: archive.read(name)
            for name in archive.namelist()
            if not name.endswith("/")
        }
    entries[target] = content
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, body in entries.items():
            archive.writestr(name, body)


def test_post_preview_returns_plan_without_writing(monkeypatch, tmp_path):
    client, _db_path, data_dir, backup_root = _client(monkeypatch, tmp_path)
    with client as active_client:
        _seed_managed_files(data_dir)
        response = active_client.post(
            "/backups/preview",
            json={
                "backup_root": str(backup_root),
                "include_data_dir": True,
                "include_proof_packets": True,
            },
        )

        assert response.status_code == 200
        payload = response.json()
        planned_paths = {file["relative_path"] for file in payload["planned_files"]}
        assert "db/proofflow.db" in planned_paths
        assert "data/input.txt" in planned_paths
        assert "proof_packets/packet.md" in planned_paths
        assert payload["would_create_case"] is True
        assert not backup_root.exists()
        assert _count_backups() == 0


def test_create_list_detail_and_verify_happy_path(monkeypatch, tmp_path):
    client, _db_path, data_dir, backup_root = _client(monkeypatch, tmp_path)
    with client as active_client:
        _seed_managed_files(data_dir)
        create_response = active_client.post(
            "/backups",
            json={"backup_root": str(backup_root), "label": "before-next-sprint"},
        )
        assert create_response.status_code == 201
        created = create_response.json()
        assert Path(created["archive_path"]).exists()
        assert Path(created["manifest_path"]).exists()

        list_response = active_client.get("/backups")
        assert list_response.status_code == 200
        listed = list_response.json()["backups"]
        assert [item["backup_id"] for item in listed] == [created["backup_id"]]
        assert listed[0]["status"] == "created"

        detail_response = active_client.get(f"/backups/{created['backup_id']}")
        assert detail_response.status_code == 200
        detail = detail_response.json()
        assert detail["backup_id"] == created["backup_id"]
        assert detail["manifest"]["manifest_version"] == "1"
        assert detail["verification"]["status"] == "not_verified"

        verify_response = active_client.post(
            f"/backups/{created['backup_id']}/verify",
            json={"recompute_archive_hash": True, "recompute_file_hashes": True},
        )
        assert verify_response.status_code == 200
        verified = verify_response.json()
        assert verified["status"] == "verified"
        assert verified["checked_files"] >= 3
        assert verified["hash_mismatches"] == []
        assert verified["missing_files"] == []

        verified_detail = active_client.get(f"/backups/{created['backup_id']}").json()
        assert verified_detail["verification"]["status"] == "verified"
        assert verified_detail["verification"]["verified_at"] is not None


def test_verify_failure_surfaces_missing_archive_and_hash_mismatch(monkeypatch, tmp_path):
    client, _db_path, data_dir, backup_root = _client(monkeypatch, tmp_path)
    with client as active_client:
        _seed_managed_files(data_dir)
        missing_archive = active_client.post(
            "/backups",
            json={"backup_root": str(backup_root)},
        ).json()
        Path(missing_archive["archive_path"]).unlink()

        missing_response = active_client.post(
            f"/backups/{missing_archive['backup_id']}/verify",
            json={},
        )
        assert missing_response.status_code == 200
        missing_payload = missing_response.json()
        assert missing_payload["status"] == "failed"
        assert any("archive file is missing" in warning for warning in missing_payload["warnings"])

        mismatched = active_client.post(
            "/backups",
            json={"backup_root": str(backup_root)},
        ).json()
        _rewrite_zip_member(Path(mismatched["archive_path"]), "data/input.txt", b"tampered")

        mismatch_response = active_client.post(
            f"/backups/{mismatched['backup_id']}/verify",
            json={},
        )
        assert mismatch_response.status_code == 200
        mismatch_payload = mismatch_response.json()
        assert mismatch_payload["status"] == "failed"
        assert any(
            mismatch["relative_path"] == "data/input.txt"
            for mismatch in mismatch_payload["hash_mismatches"]
        )


def test_unknown_backup_id_returns_404(monkeypatch, tmp_path):
    client, _db_path, _data_dir, _backup_root = _client(monkeypatch, tmp_path)
    with client as active_client:
        assert active_client.get("/backups/missing").status_code == 404
        assert active_client.post("/backups/missing/verify", json={}).status_code == 404


def test_backup_root_inside_live_data_dir_is_rejected(monkeypatch, tmp_path):
    client, _db_path, data_dir, _backup_root = _client(monkeypatch, tmp_path)
    with client as active_client:
        _seed_managed_files(data_dir)
        response = active_client.post(
            "/backups",
            json={"backup_root": str(data_dir / "unsafe-backups")},
        )
        assert response.status_code == 400
        assert "data_dir" in response.json()["detail"]


def test_backup_root_that_is_file_returns_400(monkeypatch, tmp_path):
    client, _db_path, data_dir, backup_root = _client(monkeypatch, tmp_path)
    with client as active_client:
        _seed_managed_files(data_dir)
        backup_root.write_text("not a directory", encoding="utf-8")
        response = active_client.post(
            "/backups",
            json={"backup_root": str(backup_root)},
        )
        assert response.status_code == 400
        assert "directory" in response.json()["detail"]


def test_restore_endpoints_are_not_exposed_in_phase2(monkeypatch, tmp_path):
    client, _db_path, _data_dir, _backup_root = _client(monkeypatch, tmp_path)
    with client as active_client:
        assert active_client.post("/restore/preview", json={}).status_code == 404
        assert active_client.post("/restore/to-new-location", json={}).status_code == 404
