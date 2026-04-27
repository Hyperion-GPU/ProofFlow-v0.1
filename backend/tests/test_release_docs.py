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
    bug_bash_link = "docs/releases/V0_1_0_RC1_BUG_BASH.md"

    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    checklist = (repo_root / "docs" / "V0_1_RC_CHECKLIST.md").read_text(
        encoding="utf-8"
    )
    changelog = (repo_root / "CHANGELOG.md").read_text(encoding="utf-8")

    assert bug_bash_link in readme
    assert "releases/V0_1_0_RC1_BUG_BASH.md" in checklist
    assert "post-RC1 `main` helper" in checklist
    assert "Do not move the" in checklist

    unreleased_index = changelog.index("## Unreleased")
    rc1_index = changelog.index("## v0.1.0-rc1")
    smoke_index = changelog.index("scripts/rc_api_smoke.py")
    demo_index = changelog.index("scripts/demo_seed.py")

    assert unreleased_index < smoke_index < rc1_index
    assert unreleased_index < demo_index < rc1_index


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
