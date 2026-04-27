from pathlib import Path
import tempfile

from fastapi.testclient import TestClient

from proofflow.main import app


def _client(monkeypatch, temp_root: Path) -> TestClient:
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(temp_root / "actions.db"))
    monkeypatch.setenv("PROOFFLOW_DATA_DIR", str(temp_root / "data"))
    return TestClient(app)


def _create_case(client: TestClient) -> str:
    response = client.post(
        "/cases",
        json={"title": "File cleanup", "kind": "file_cleanup"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _create_file_action(
    client: TestClient,
    case_id: str,
    kind: str,
    source: Path,
    destination: Path,
) -> dict:
    response = client.post(
        "/actions",
        json={
            "case_id": case_id,
            "kind": kind,
            "title": f"{kind} action",
            "reason": "test safe file operation",
            "preview": {
                "from_path": str(source),
                "to_path": str(destination),
            },
            "metadata": _scope_metadata(source.parent, destination.parent),
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_mkdir_action(client: TestClient, case_id: str, directory: Path) -> dict:
    response = client.post(
        "/actions",
        json={
            "case_id": case_id,
            "kind": "mkdir_dir",
            "title": "Create directory",
            "reason": "test safe directory operation",
            "preview": {
                "dir_path": str(directory),
            },
            "metadata": _scope_metadata(directory.parent),
        },
    )
    assert response.status_code == 201
    return response.json()


def _scope_metadata(*roots: Path) -> dict:
    return {
        "scope_kind": "test_file_action",
        "allowed_roots": [str(root.resolve(strict=False)) for root in roots],
    }


def test_move_file_lifecycle(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        source = temp_root / "source.txt"
        destination = temp_root / "moved.txt"
        source.write_text("move me", encoding="utf-8")

        with _client(monkeypatch, temp_root) as client:
            case_id = _create_case(client)
            action = _create_file_action(client, case_id, "move_file", source, destination)
            assert action["status"] == "previewed"
            assert source.exists()
            assert not destination.exists()

            list_response = client.get(f"/cases/{case_id}/actions")
            assert list_response.status_code == 200
            assert [item["id"] for item in list_response.json()] == [action["id"]]

            approved = client.post(f"/actions/{action['id']}/approve")
            assert approved.status_code == 200
            assert approved.json()["status"] == "approved"

            executed = client.post(f"/actions/{action['id']}/execute")
            assert executed.status_code == 200
            executed_payload = executed.json()
            assert executed_payload["status"] == "executed"
            assert executed_payload["result"]["from_path"] == str(source)
            assert executed_payload["result"]["to_path"] == str(destination)
            assert executed_payload["undo"]["from_path"] == str(destination)
            assert not source.exists()
            assert destination.read_text(encoding="utf-8") == "move me"

            undone = client.post(f"/actions/{action['id']}/undo")
            assert undone.status_code == 200
            assert undone.json()["status"] == "undone"
            assert source.read_text(encoding="utf-8") == "move me"
            assert not destination.exists()


def test_mkdir_dir_lifecycle(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        directory = temp_root / "sorted" / "Notes"

        with _client(monkeypatch, temp_root) as client:
            case_id = _create_case(client)
            action = _create_mkdir_action(client, case_id, directory)
            assert action["status"] == "previewed"
            assert not directory.exists()

            approved = client.post(f"/actions/{action['id']}/approve")
            assert approved.status_code == 200

            executed = client.post(f"/actions/{action['id']}/execute")
            assert executed.status_code == 200
            executed_payload = executed.json()
            assert executed_payload["status"] == "executed"
            assert executed_payload["result"]["created"] is True
            assert executed_payload["result"]["already_exists"] is False
            assert executed_payload["undo"]["created_by_action"] is True
            assert directory.is_dir()

            undone = client.post(f"/actions/{action['id']}/undo")
            assert undone.status_code == 200
            assert undone.json()["status"] == "undone"
            assert undone.json()["undo"]["removed"] is True
            assert not directory.exists()


def test_mkdir_dir_execute_accepts_existing_directory_without_undo_delete(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        directory = temp_root / "existing"
        directory.mkdir()

        with _client(monkeypatch, temp_root) as client:
            case_id = _create_case(client)
            action = _create_mkdir_action(client, case_id, directory)
            client.post(f"/actions/{action['id']}/approve")

            executed = client.post(f"/actions/{action['id']}/execute")
            assert executed.status_code == 200
            assert executed.json()["result"]["created"] is False
            assert executed.json()["result"]["already_exists"] is True

            undone = client.post(f"/actions/{action['id']}/undo")
            assert undone.status_code == 200
            assert undone.json()["undo"]["removed"] is False
            assert directory.is_dir()


def test_mkdir_dir_undo_refuses_non_empty_directory(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        directory = temp_root / "sorted" / "Logs"

        with _client(monkeypatch, temp_root) as client:
            case_id = _create_case(client)
            action = _create_mkdir_action(client, case_id, directory)
            client.post(f"/actions/{action['id']}/approve")
            executed = client.post(f"/actions/{action['id']}/execute")
            assert executed.status_code == 200

            marker = directory / "keep.log"
            marker.write_text("keep me", encoding="utf-8")
            undo = client.post(f"/actions/{action['id']}/undo")
            assert undo.status_code == 400
            assert marker.read_text(encoding="utf-8") == "keep me"
            assert directory.is_dir()


def test_create_action_rejects_preview_shape_that_does_not_match_kind(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)

        with _client(monkeypatch, temp_root) as client:
            case_id = _create_case(client)
            move_with_dir_preview = client.post(
                "/actions",
                json={
                    "case_id": case_id,
                    "kind": "move_file",
                    "title": "Bad move",
                    "reason": "dir preview does not describe a file move",
                    "preview": {"dir_path": str(temp_root / "Notes")},
                },
            )
            mkdir_with_file_preview = client.post(
                "/actions",
                json={
                    "case_id": case_id,
                    "kind": "mkdir_dir",
                    "title": "Bad mkdir",
                    "reason": "file preview does not describe a directory create",
                    "preview": {
                        "from_path": str(temp_root / "source.txt"),
                        "to_path": str(temp_root / "target.txt"),
                    },
                },
            )
            manual_with_preview = client.post(
                "/actions",
                json={
                    "case_id": case_id,
                    "kind": "manual_check",
                    "title": "Bad manual check",
                    "reason": "manual checks do not execute a previewed operation",
                    "preview": {"dir_path": str(temp_root / "Notes")},
                },
            )

        assert move_with_dir_preview.status_code == 422
        assert mkdir_with_file_preview.status_code == 422
        assert manual_with_preview.status_code == 422


def test_filesystem_action_requires_scope_metadata(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        source = temp_root / "source.txt"
        destination = temp_root / "moved.txt"
        source.write_text("scope me", encoding="utf-8")

        with _client(monkeypatch, temp_root) as client:
            case_id = _create_case(client)
            response = client.post(
                "/actions",
                json={
                    "case_id": case_id,
                    "kind": "move_file",
                    "title": "Missing scope",
                    "reason": "filesystem actions need explicit roots",
                    "preview": {
                        "from_path": str(source),
                        "to_path": str(destination),
                    },
                },
            )

        assert response.status_code == 400
        assert "metadata.allowed_roots" in response.json()["detail"]


def test_filesystem_action_refuses_proofflow_data_paths(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        source = temp_root / "source.txt"
        protected_destination = temp_root / "data" / "proof_packets" / "packet.md"
        source.write_text("do not move into data", encoding="utf-8")

        with _client(monkeypatch, temp_root) as client:
            case_id = _create_case(client)
            response = client.post(
                "/actions",
                json={
                    "case_id": case_id,
                    "kind": "move_file",
                    "title": "Protected destination",
                    "reason": "ProofFlow data is not an action target",
                    "preview": {
                        "from_path": str(source),
                        "to_path": str(protected_destination),
                    },
                    "metadata": _scope_metadata(temp_root),
                },
            )

        assert response.status_code == 400
        assert "ProofFlow proof_packets directory" in response.json()["detail"]


def test_rename_file_lifecycle(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        source = temp_root / "old-name.txt"
        destination = temp_root / "new-name.txt"
        source.write_text("rename me", encoding="utf-8")

        with _client(monkeypatch, temp_root) as client:
            case_id = _create_case(client)
            action = _create_file_action(client, case_id, "rename_file", source, destination)
            client.post(f"/actions/{action['id']}/approve")

            executed = client.post(f"/actions/{action['id']}/execute")
            assert executed.status_code == 200
            assert executed.json()["status"] == "executed"
            assert not source.exists()
            assert destination.exists()

            undone = client.post(f"/actions/{action['id']}/undo")
            assert undone.status_code == 200
            assert source.exists()
            assert not destination.exists()


def test_reject_prevents_execute(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        source = temp_root / "source.txt"
        destination = temp_root / "moved.txt"
        source.write_text("reject me", encoding="utf-8")

        with _client(monkeypatch, temp_root) as client:
            case_id = _create_case(client)
            action = _create_file_action(client, case_id, "move_file", source, destination)

            rejected = client.post(f"/actions/{action['id']}/reject")
            assert rejected.status_code == 200
            assert rejected.json()["status"] == "rejected"

            execute = client.post(f"/actions/{action['id']}/execute")
            assert execute.status_code == 400
            assert source.exists()
            assert not destination.exists()


def test_execute_refuses_overwrite(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        source = temp_root / "source.txt"
        destination = temp_root / "existing.txt"
        source.write_text("source", encoding="utf-8")
        destination.write_text("destination", encoding="utf-8")

        with _client(monkeypatch, temp_root) as client:
            case_id = _create_case(client)
            action = _create_file_action(client, case_id, "move_file", source, destination)
            client.post(f"/actions/{action['id']}/approve")

            execute = client.post(f"/actions/{action['id']}/execute")
            assert execute.status_code == 400
            assert source.read_text(encoding="utf-8") == "source"
            assert destination.read_text(encoding="utf-8") == "destination"


def test_undo_refuses_when_original_source_path_is_occupied(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        source = temp_root / "source.txt"
        destination = temp_root / "moved.txt"
        source.write_text("source", encoding="utf-8")

        with _client(monkeypatch, temp_root) as client:
            case_id = _create_case(client)
            action = _create_file_action(client, case_id, "move_file", source, destination)
            client.post(f"/actions/{action['id']}/approve")

            execute = client.post(f"/actions/{action['id']}/execute")
            assert execute.status_code == 200
            source.write_text("occupier", encoding="utf-8")

            undo = client.post(f"/actions/{action['id']}/undo")
            assert undo.status_code == 400
            assert source.read_text(encoding="utf-8") == "occupier"
            assert destination.read_text(encoding="utf-8") == "source"


def test_undo_refuses_when_moved_file_hash_changed(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        source = temp_root / "source.txt"
        destination = temp_root / "moved.txt"
        source.write_text("source", encoding="utf-8")

        with _client(monkeypatch, temp_root) as client:
            case_id = _create_case(client)
            action = _create_file_action(client, case_id, "move_file", source, destination)
            client.post(f"/actions/{action['id']}/approve")

            execute = client.post(f"/actions/{action['id']}/execute")
            assert execute.status_code == 200
            destination.write_text("changed after execution", encoding="utf-8")

            undo = client.post(f"/actions/{action['id']}/undo")
            assert undo.status_code == 400
            assert not source.exists()
            assert destination.read_text(encoding="utf-8") == "changed after execution"


def test_manual_check_never_touches_files(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        marker = temp_root / "marker.txt"
        marker.write_text("unchanged", encoding="utf-8")

        with _client(monkeypatch, temp_root) as client:
            case_id = _create_case(client)
            create_response = client.post(
                "/actions",
                json={
                    "case_id": case_id,
                    "kind": "manual_check",
                    "title": "Review manually",
                    "reason": "needs human judgment",
                },
            )
            assert create_response.status_code == 201
            action = create_response.json()

            approved = client.post(f"/actions/{action['id']}/approve")
            assert approved.status_code == 200

            executed = client.post(f"/actions/{action['id']}/execute")
            assert executed.status_code == 200
            assert executed.json()["status"] == "executed"
            assert executed.json()["result"]["touched_files"] is False
            assert marker.read_text(encoding="utf-8") == "unchanged"

            undo = client.post(f"/actions/{action['id']}/undo")
            assert undo.status_code == 400
            assert marker.read_text(encoding="utf-8") == "unchanged"
