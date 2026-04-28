from pathlib import Path
import importlib.util
import sys


def _load_backup_restore_api_smoke_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "backup_restore_api_smoke.py"
    spec = importlib.util.spec_from_file_location("prooflow_backup_restore_api_smoke", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fake_smoke_result(root: Path) -> dict:
    target_db_path = root / "restore" / "proofflow-restored.db"
    target_data_dir = root / "restore" / "data"
    target_db_path.parent.mkdir(parents=True)
    target_db_path.write_text("sqlite placeholder\n", encoding="utf-8")
    target_data_dir.mkdir(parents=True)
    return {
        "temp_root": str(root),
        "db_path": str(root / "proofflow-backup-restore-smoke.db"),
        "data_dir": str(root / "data"),
        "backup_root": str(root / "backups"),
        "backup_id": "backup-1",
        "backup_preview_files": 2,
        "backups_listed": 1,
        "backup_detail_status": "not_verified",
        "verification_status": "verified",
        "restore_preview_id": "preview-1",
        "restore_planned_writes": 2,
        "restore_status": "restored_to_new_location",
        "restored_files": 2,
        "target_db_path": str(target_db_path),
        "target_data_dir": str(target_data_dir),
        "health": {"ok": True},
    }


def test_backup_restore_api_smoke_main_keeps_default_temp_artifacts(
    monkeypatch,
    tmp_path,
    capsys,
):
    module = _load_backup_restore_api_smoke_module()
    temp_root = tmp_path / "proofflow-backup-restore-smoke-test"

    def fake_mkdtemp(prefix: str) -> str:
        assert prefix == "proofflow-backup-restore-smoke-"
        temp_root.mkdir()
        return str(temp_root)

    monkeypatch.setattr(module.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(module, "run_smoke", _fake_smoke_result)

    assert module.main([]) == 0

    output = capsys.readouterr().out
    assert "ProofFlow backup/restore API smoke passed." in output
    assert "Temp root retained for inspection" in output
    assert temp_root.exists()
    assert (temp_root / "restore" / "proofflow-restored.db").exists()


def test_backup_restore_api_smoke_cleanup_removes_generated_temp_artifacts(
    monkeypatch,
    tmp_path,
):
    module = _load_backup_restore_api_smoke_module()
    temp_root = tmp_path / "proofflow-backup-restore-smoke-cleanup"

    def fake_mkdtemp(prefix: str) -> str:
        assert prefix == "proofflow-backup-restore-smoke-"
        temp_root.mkdir()
        return str(temp_root)

    monkeypatch.setattr(module.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(module, "run_smoke", _fake_smoke_result)

    assert module.main(["--cleanup"]) == 0

    assert not temp_root.exists()


def test_backup_restore_api_smoke_cleanup_keeps_temp_artifacts_after_failure(
    monkeypatch,
    tmp_path,
    capsys,
):
    module = _load_backup_restore_api_smoke_module()
    temp_root = tmp_path / "proofflow-backup-restore-smoke-failure"

    def fake_mkdtemp(prefix: str) -> str:
        assert prefix == "proofflow-backup-restore-smoke-"
        temp_root.mkdir()
        return str(temp_root)

    def fake_run_smoke(root: Path) -> dict:
        evidence_path = root / "failure-evidence.txt"
        evidence_path.write_text("keep failure evidence\n", encoding="utf-8")
        raise RuntimeError("simulated smoke failure")

    monkeypatch.setattr(module.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(module, "run_smoke", fake_run_smoke)

    assert module.main(["--cleanup"]) == 1

    error_output = capsys.readouterr().err
    assert "simulated smoke failure" in error_output
    assert temp_root.exists()
    assert (temp_root / "failure-evidence.txt").read_text(
        encoding="utf-8"
    ) == "keep failure evidence\n"


def test_backup_restore_api_smoke_rejects_repo_live_data_paths():
    module = _load_backup_restore_api_smoke_module()

    try:
        module._assert_isolated_paths(module.REPO_LIVE_DATA_ROOT / "proofflow.db")
    except RuntimeError as error:
        assert "repo live data path" in str(error)
    else:
        raise AssertionError("repo live data path was not rejected")
