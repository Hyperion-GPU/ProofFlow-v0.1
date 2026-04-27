from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "docs" / "managed_backup_restore.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"


def _doc() -> str:
    return DOC_PATH.read_text(encoding="utf-8")


def test_managed_backup_restore_design_doc_exists():
    assert DOC_PATH.exists()


def test_design_doc_includes_required_invariants():
    content = _doc()
    required = [
        "No Manifest, no Backup.",
        "No Verify, no trusted Backup.",
        "No Preview, no Restore.",
        "No Pre-restore Backup, no destructive Restore.",
        "No Hash Match, no Restore.",
        "No Source Version, no Restore Trust.",
    ]
    for invariant in required:
        assert invariant in content


def test_design_doc_blocks_live_db_restore_in_foundation_phase():
    content = _doc()
    assert "foundation phase does not restore into the live db" in content.lower()
    assert "No Restore to live DB in foundation phase." in content


def test_design_doc_includes_proposed_endpoint_names():
    content = _doc()
    endpoints = [
        "POST /backups/preview",
        "POST /backups",
        "GET /backups",
        "GET /backups/{backup_id}",
        "POST /backups/{backup_id}/verify",
        "POST /restore/preview",
        "POST /restore/to-new-location",
    ]
    for endpoint in endpoints:
        assert endpoint in content


def test_design_doc_includes_manifest_required_fields():
    content = _doc()
    fields = [
        "manifest_version",
        "app_name",
        "app_version",
        "schema_version",
        "created_at",
        "backup_id",
        "db_path",
        "data_dir",
        "proof_packets_dir",
        "files",
        "role",
        "relative_path",
        "size_bytes",
        "sha256",
        "mtime",
        "archive",
        "format",
        "warnings",
    ]
    for field in fields:
        assert field in content


def test_design_doc_excludes_localproof_source_root_bulk_archives_by_default():
    content = _doc()
    assert "No LocalProof source-root bulk archiving by default." in content
    assert "LocalProof source roots are not bulk archived by default." in content


def test_agents_includes_backup_restore_invariants():
    content = AGENTS_PATH.read_text(encoding="utf-8")
    required = [
        "No Manifest, no Backup.",
        "No Verify, no trusted Backup.",
        "No Preview, no Restore.",
        "No Pre-restore Backup, no destructive Restore.",
        "No Hash Match, no Restore.",
        "No Source Version, no Restore Trust.",
        "No Restore to live DB in foundation phase.",
    ]
    for invariant in required:
        assert invariant in content
