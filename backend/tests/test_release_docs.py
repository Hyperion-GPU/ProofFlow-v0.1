from pathlib import Path


def test_rc1_bug_bash_doc_has_release_guardrails_and_no_secret_examples():
    repo_root = Path(__file__).resolve().parents[2]
    doc_path = repo_root / "docs" / "releases" / "V0_1_0_RC1_BUG_BASH.md"
    content = doc_path.read_text(encoding="utf-8")
    lowered = content.lower()

    required = [
        "ProofFlow v0.1.0-rc1 Dogfood Bug Bash",
        "Do not move",
        "v0.1.0-rc1",
        "v0.1.0-rc2",
        "allowed_roots",
        "Proof Packet",
    ]
    for text in required:
        assert text in content

    assert (
        "scripts\\rc_api_smoke.py" in content
        or "scripts/rc_api_smoke.py" in content
    )
    assert "sensitive untracked" in lowered

    forbidden = [
        "BEGIN PRIVATE KEY",
        "SECRET=",
        "TOKEN=",
        "C:\\Users\\",
        "/home/",
    ]
    for text in forbidden:
        assert text not in content


def test_rc1_bug_bash_links_and_changelog_unreleased_scope():
    repo_root = Path(__file__).resolve().parents[2]

    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    changelog = (repo_root / "CHANGELOG.md").read_text(encoding="utf-8")

    # README should reference key project elements
    assert "ProofFlow" in readme
    assert "MCP" in readme
    assert "docker compose" in readme.lower() or "docker-compose" in readme.lower()
    assert "127.0.0.1" in readme
    assert "PROOFFLOW_API_KEY" in readme
    assert "PROOFFLOW_ENABLE_TEST_COMMANDS" in readme

    # Changelog structure still valid
    assert "## Unreleased" in changelog
    assert "## v0.1.0-rc1" in changelog


def test_rc1_bug_bash_commands_return_to_repo_root():
    repo_root = Path(__file__).resolve().parents[2]
    content = (
        repo_root / "docs" / "releases" / "V0_1_0_RC1_BUG_BASH.md"
    ).read_text(encoding="utf-8")

    assert "cd .\\backend" not in content
    assert "cd .\\frontend" not in content
    assert "cd backend;" not in content
    assert "cd frontend;" not in content
    assert "Push-Location .\\backend" in content
    assert "Push-Location .\\frontend" in content
    assert content.count("Pop-Location") >= 3
