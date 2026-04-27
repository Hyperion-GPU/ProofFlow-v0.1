from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import sys

import pytest

from proofflow.db import connect


def _load_demo_seed_module():
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "scripts" / "demo_seed.py"
    spec = importlib.util.spec_from_file_location("prooflow_demo_seed", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_demo_seed_creates_repeatable_sample_data(monkeypatch, tmp_path):
    module = _load_demo_seed_module()
    source_repo_root = Path(__file__).resolve().parents[2]
    repo_root = tmp_path / "prooflow-demo-root"
    repo_root.mkdir()
    _copy_sample_fixtures(source_repo_root, repo_root)
    fixture_hashes_before = _hash_tree(repo_root / "sample_data" / "files")

    db_path = repo_root / "backend" / "data" / "demo" / "proofflow.db"
    data_dir = repo_root / "backend" / "data" / "demo"
    git_available = shutil.which("git") is not None

    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(db_path))
    monkeypatch.setenv("PROOFFLOW_DATA_DIR", str(data_dir))

    first = module.seed_demo(
        repo_root=repo_root,
        db_path=db_path,
        data_dir=data_dir,
        include_agentguard=git_available,
    )
    second = module.seed_demo(
        repo_root=repo_root,
        db_path=db_path,
        data_dir=data_dir,
        include_agentguard=git_available,
    )

    assert first.db_path == second.db_path
    assert second.db_path.exists()
    assert second.proof_packet_path.exists()
    assert _hash_tree(repo_root / "sample_data" / "files") == fixture_hashes_before
    assert _is_under(second.db_path, repo_root)
    assert _is_under(second.data_dir, repo_root)
    assert _is_under(second.proof_packet_path, repo_root)

    with connect(second.db_path) as connection:
        case_counts = {
            row["case_type"]: row["count"]
            for row in connection.execute(
                "SELECT case_type, COUNT(*) AS count FROM cases GROUP BY case_type"
            ).fetchall()
        }
        proof_packets = connection.execute(
            "SELECT COUNT(*) FROM artifacts WHERE artifact_type = 'proof_packet'"
        ).fetchone()[0]
        actions = connection.execute("SELECT COUNT(*) FROM actions").fetchone()[0]
        decisions = connection.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
        artifact_metadata = connection.execute(
            "SELECT metadata_json FROM artifacts"
        ).fetchall()

    assert case_counts["local_proof"] == 1
    assert case_counts["file_cleanup"] == 1
    if git_available:
        assert case_counts["code_review"] == 1
        assert second.agentguard_case_id is not None
        assert second.agentguard_skipped_reason is None
    else:
        assert second.agentguard_case_id is None
        assert second.agentguard_skipped_reason
    assert proof_packets >= 1
    assert actions >= 2
    assert decisions == 1

    for row in artifact_metadata:
        metadata = json.loads(row["metadata_json"])
        for key in ("path", "repo_path"):
            value = metadata.get(key)
            if isinstance(value, str) and value:
                assert _is_under(Path(value), repo_root)


def test_demo_seed_rejects_reset_outside_demo_data(monkeypatch, tmp_path):
    module = _load_demo_seed_module()
    source_repo_root = Path(__file__).resolve().parents[2]
    repo_root = tmp_path / "prooflow-demo-root"
    repo_root.mkdir()
    _copy_sample_fixtures(source_repo_root, repo_root)
    protected_dir = repo_root / "docs"
    protected_dir.mkdir()
    marker = protected_dir / "keep.txt"
    marker.write_text("do not delete\n", encoding="utf-8")

    db_path = protected_dir / "proofflow.db"
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(db_path))
    monkeypatch.setenv("PROOFFLOW_DATA_DIR", str(protected_dir))

    with pytest.raises(RuntimeError, match="outside allowed demo root"):
        module.seed_demo(
            repo_root=repo_root,
            db_path=db_path,
            data_dir=protected_dir,
            include_agentguard=False,
        )

    assert marker.read_text(encoding="utf-8") == "do not delete\n"


def test_demo_seed_cli_honors_env_output_paths(monkeypatch, tmp_path):
    module = _load_demo_seed_module()
    source_repo_root = Path(__file__).resolve().parents[2]
    repo_root = tmp_path / "prooflow-demo-root"
    repo_root.mkdir()
    _copy_sample_fixtures(source_repo_root, repo_root)

    data_dir = tmp_path / "isolated-smoke" / "data"
    db_path = data_dir / "proofflow.db"
    monkeypatch.setattr(module, "REPO_ROOT", repo_root)
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(db_path))
    monkeypatch.setenv("PROOFFLOW_DATA_DIR", str(data_dir))

    module.main(["--no-agentguard"])

    assert db_path.exists()
    assert data_dir.exists()
    assert (data_dir / module.DEMO_DATA_MARKER).exists()
    assert (repo_root / "sample_data" / "work" / "files").exists()
    assert not (repo_root / "backend" / "data" / "demo" / "proofflow.db").exists()

    with connect(db_path) as connection:
        case_count = connection.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        proof_packets = connection.execute(
            "SELECT COUNT(*) FROM artifacts WHERE artifact_type = 'proof_packet'"
        ).fetchone()[0]

    assert case_count == 2
    assert proof_packets >= 1


def test_demo_seed_rejects_non_empty_custom_temp_data_dir_without_marker(
    tmp_path,
):
    module = _load_demo_seed_module()
    source_repo_root = Path(__file__).resolve().parents[2]
    repo_root = tmp_path / "prooflow-demo-root"
    repo_root.mkdir()
    _copy_sample_fixtures(source_repo_root, repo_root)

    data_dir = tmp_path / "preexisting-data"
    data_dir.mkdir()
    marker = data_dir / "keep.txt"
    marker.write_text("keep me\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="custom demo data directory"):
        module.seed_demo(
            repo_root=repo_root,
            db_path=data_dir / "proofflow.db",
            data_dir=data_dir,
            include_agentguard=False,
        )

    assert marker.read_text(encoding="utf-8") == "keep me\n"


def test_demo_seed_remove_tree_retries_readonly_paths(tmp_path):
    module = _load_demo_seed_module()
    target = tmp_path / "readonly-tree"
    target.mkdir()
    readonly_file = target / "readonly.txt"
    readonly_file.write_text("readonly\n", encoding="utf-8")
    readonly_file.chmod(stat.S_IREAD)

    try:
        module._remove_tree(target)
    finally:
        if readonly_file.exists():
            os.chmod(readonly_file, stat.S_IWRITE)

    assert not target.exists()


def test_demo_seed_png_fixture_has_real_png_signature():
    repo_root = Path(__file__).resolve().parents[2]
    png_path = repo_root / "sample_data" / "files" / "images" / "diagram.png"
    assert png_path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _copy_sample_fixtures(source_repo_root: Path, target_repo_root: Path) -> None:
    source = source_repo_root / "sample_data" / "files"
    destination = target_repo_root / "sample_data" / "files"
    shutil.copytree(source, destination)


def _hash_tree(root: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes
