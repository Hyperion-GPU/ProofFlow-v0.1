from pathlib import Path
import importlib.util
import sys


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
