from pathlib import Path

from fastapi.testclient import TestClient

from proofflow.main import app


def _client(monkeypatch, tmp_path: Path) -> TestClient:
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(tmp_path / "v01-acceptance.db"))
    monkeypatch.setenv("PROOFFLOW_DATA_DIR", str(tmp_path / "data"))
    return TestClient(app)


def _scope_metadata(*roots: Path) -> dict:
    return {
        "scope_kind": "acceptance_file_action",
        "allowed_roots": [str(root.resolve(strict=False)) for root in roots],
    }


def test_v01_action_lifecycle_is_reflected_in_case_packet(monkeypatch, tmp_path):
    source_dir = tmp_path / "inbox"
    source_dir.mkdir()
    source = source_dir / "notes.md"
    source.write_text("# Dogfood note\n", encoding="utf-8")
    target_dir = tmp_path / "sorted" / "Notes"
    destination = target_dir / "notes.md"

    with _client(monkeypatch, tmp_path) as client:
        case_response = client.post(
            "/cases",
            json={
                "title": "Dogfood action lifecycle",
                "kind": "file_cleanup",
                "summary": "Acceptance test for v0.1 action invariants.",
            },
        )
        assert case_response.status_code == 201
        case_id = case_response.json()["id"]

        mkdir_response = client.post(
            "/actions",
            json={
                "case_id": case_id,
                "kind": "mkdir_dir",
                "title": "Create Notes directory",
                "reason": "Previewable directory prerequisite.",
                "preview": {"dir_path": str(target_dir)},
                "metadata": _scope_metadata(target_dir.parent),
            },
        )
        assert mkdir_response.status_code == 201
        mkdir_action = mkdir_response.json()

        move_response = client.post(
            "/actions",
            json={
                "case_id": case_id,
                "kind": "move_file",
                "title": "Move note into Notes",
                "reason": "Previewable file move.",
                "preview": {
                    "from_path": str(source),
                    "to_path": str(destination),
                },
                "metadata": {
                    **_scope_metadata(source_dir, target_dir),
                    "depends_on_action_id": mkdir_action["id"],
                    "depends_on_dir_path": str(target_dir),
                },
            },
        )
        assert move_response.status_code == 201
        move_action = move_response.json()

        execute_without_approval = client.post(f"/actions/{move_action['id']}/execute")
        assert execute_without_approval.status_code == 400
        assert source.exists()
        assert not destination.exists()

        assert client.post(f"/actions/{mkdir_action['id']}/approve").status_code == 200
        executed_mkdir = client.post(f"/actions/{mkdir_action['id']}/execute")
        assert executed_mkdir.status_code == 200
        assert executed_mkdir.json()["result"]["created"] is True
        assert target_dir.is_dir()

        assert client.post(f"/actions/{move_action['id']}/approve").status_code == 200
        executed_move = client.post(f"/actions/{move_action['id']}/execute")
        assert executed_move.status_code == 200
        assert not source.exists()
        assert destination.read_text(encoding="utf-8") == "# Dogfood note\n"

        undone_move = client.post(f"/actions/{move_action['id']}/undo")
        assert undone_move.status_code == 200
        assert source.read_text(encoding="utf-8") == "# Dogfood note\n"
        assert not destination.exists()

        undone_mkdir = client.post(f"/actions/{mkdir_action['id']}/undo")
        assert undone_mkdir.status_code == 200
        assert not target_dir.exists()

        packet_response = client.get(f"/cases/{case_id}/packet")

    assert packet_response.status_code == 200
    packet = packet_response.json()
    actions = {action["id"]: action for action in packet["actions"]}

    assert actions[mkdir_action["id"]]["status"] == "undone"
    assert actions[mkdir_action["id"]]["result"]["operation"] == "mkdir_dir"
    assert actions[mkdir_action["id"]]["undo"]["removed"] is True

    assert actions[move_action["id"]]["status"] == "undone"
    assert actions[move_action["id"]]["result"]["operation"] == "move_file"
    assert actions[move_action["id"]]["undo"]["operation"] == "restore_file"
    assert actions[move_action["id"]]["metadata"]["depends_on_action_id"] == mkdir_action["id"]
