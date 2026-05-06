from pathlib import Path
import importlib.util
import sys

import pytest


pytestmark = pytest.mark.no_bypass_policy_gate


def _load_rc_api_smoke_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "rc_api_smoke.py"
    spec = importlib.util.spec_from_file_location("prooflow_rc_api_smoke", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_rc_api_smoke_release_identity_uses_backend_version():
    module = _load_rc_api_smoke_module()

    health = {
        "ok": True,
        "service": "proofflow-backend",
        "version": module.__version__,
        "release_stage": module.release_stage,
        "release_name": module.release_name,
    }

    module._assert_release_identity(health)


def test_rc_api_smoke_release_identity_rejects_stale_version():
    module = _load_rc_api_smoke_module()

    health = {
        "ok": True,
        "service": "proofflow-backend",
        "version": "0.1.0-rc1",
        "release_stage": module.release_stage,
        "release_name": module.release_name,
    }

    with pytest.raises(RuntimeError, match="health version mismatch"):
        module._assert_release_identity(health)


def test_rc_api_smoke_main_keeps_default_temp_artifacts(
    monkeypatch,
    tmp_path,
    capsys,
):
    module = _load_rc_api_smoke_module()
    temp_root = tmp_path / "proofflow-rc-api-smoke-test"

    def fake_mkdtemp(prefix: str) -> str:
        assert prefix == "proofflow-rc-api-smoke-"
        return str(temp_root)

    def fake_run_smoke(root: Path) -> dict:
        packet_path = root / "data" / "proof_packets" / "packet.md"
        packet_path.parent.mkdir(parents=True)
        packet_path.write_text("# Packet\n", encoding="utf-8")
        return {
            "db_path": str(root / "proofflow-smoke.db"),
            "data_dir": str(root / "data"),
            "localproof": {
                "case_id": "localproof-case",
                "actions_created": 2,
            },
            "agentguard": {
                "case_id": "agentguard-case",
                "packet_path": str(packet_path),
            },
        }

    monkeypatch.setattr(module.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(module, "run_smoke", fake_run_smoke)

    assert module.main([]) == 0

    output = capsys.readouterr().out
    assert "Temp root retained for inspection" in output
    assert temp_root.exists()
    assert (temp_root / "data" / "proof_packets" / "packet.md").exists()


def test_rc_api_smoke_cleanup_removes_generated_temp_artifacts(
    monkeypatch,
    tmp_path,
):
    module = _load_rc_api_smoke_module()
    temp_root = tmp_path / "proofflow-rc-api-smoke-cleanup"

    def fake_mkdtemp(prefix: str) -> str:
        assert prefix == "proofflow-rc-api-smoke-"
        return str(temp_root)

    def fake_run_smoke(root: Path) -> dict:
        packet_path = root / "data" / "proof_packets" / "packet.md"
        packet_path.parent.mkdir(parents=True)
        packet_path.write_text("# Packet\n", encoding="utf-8")
        return {
            "db_path": str(root / "proofflow-smoke.db"),
            "data_dir": str(root / "data"),
            "localproof": {
                "case_id": "localproof-case",
                "actions_created": 2,
            },
            "agentguard": {
                "case_id": "agentguard-case",
                "packet_path": str(packet_path),
            },
        }

    monkeypatch.setattr(module.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(module, "run_smoke", fake_run_smoke)

    assert module.main(["--cleanup"]) == 0

    assert not temp_root.exists()


def test_rc_api_smoke_cleanup_keeps_temp_artifacts_after_failure(
    monkeypatch,
    tmp_path,
):
    module = _load_rc_api_smoke_module()
    temp_root = tmp_path / "proofflow-rc-api-smoke-failure"

    def fake_mkdtemp(prefix: str) -> str:
        assert prefix == "proofflow-rc-api-smoke-"
        return str(temp_root)

    def fake_run_smoke(root: Path) -> dict:
        evidence_path = root / "data" / "failure-evidence.txt"
        evidence_path.parent.mkdir(parents=True)
        evidence_path.write_text("keep failure evidence\n", encoding="utf-8")
        raise RuntimeError("simulated smoke failure")

    monkeypatch.setattr(module.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(module, "run_smoke", fake_run_smoke)

    with pytest.raises(RuntimeError, match="simulated smoke failure"):
        module.main(["--cleanup"])

    assert temp_root.exists()
    assert (temp_root / "data" / "failure-evidence.txt").read_text(
        encoding="utf-8"
    ) == "keep failure evidence\n"
