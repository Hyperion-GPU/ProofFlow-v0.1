from pathlib import Path
import importlib.util
import os
import sys
import types

import pytest


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


def test_run_smoke_enables_agentguard_test_commands_during_rc_smoke(
    monkeypatch,
    tmp_path,
):
    module = _load_rc_api_smoke_module()

    class FakeResponse:
        status_code = 200
        text = "{}"

        def json(self) -> dict:
            return {
                "ok": True,
                "service": "proofflow-backend",
                "version": "0.1.0",
                "release_stage": "stable",
                "release_name": "ProofFlow v0.1.0",
            }

    class FakeTestClient:
        def __init__(self, app: object) -> None:
            self.app = app

        def __enter__(self) -> "FakeTestClient":
            return self

        def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
            return None

        def get(self, path: str) -> FakeResponse:
            assert path == "/health"
            return FakeResponse()

    fake_testclient_module = types.ModuleType("fastapi.testclient")
    fake_testclient_module.TestClient = FakeTestClient
    fake_main_module = types.ModuleType("proofflow.main")
    fake_main_module.app = object()

    monkeypatch.setitem(sys.modules, "fastapi.testclient", fake_testclient_module)
    monkeypatch.setitem(sys.modules, "proofflow.main", fake_main_module)
    monkeypatch.delenv("PROOFFLOW_ENABLE_TEST_COMMANDS", raising=False)

    def fake_localproof(client: object, temp_root: Path) -> dict:
        assert os.environ["PROOFFLOW_ENABLE_TEST_COMMANDS"] == "true"
        return {"case_id": "localproof-case"}

    def fake_agentguard(client: object, temp_root: Path) -> dict:
        assert os.environ["PROOFFLOW_ENABLE_TEST_COMMANDS"] == "true"
        return {"case_id": "agentguard-case"}

    monkeypatch.setattr(module, "_run_localproof_action_smoke", fake_localproof)
    monkeypatch.setattr(module, "_run_agentguard_packet_smoke", fake_agentguard)

    result = module.run_smoke(tmp_path)

    assert result["agentguard"] == {"case_id": "agentguard-case"}
    assert "PROOFFLOW_ENABLE_TEST_COMMANDS" not in os.environ


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
