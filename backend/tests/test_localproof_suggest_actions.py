from pathlib import Path
import tempfile

from fastapi.testclient import TestClient

from proofflow.main import app


def _client(monkeypatch, temp_root: Path) -> TestClient:
    monkeypatch.setenv("PROOFFLOW_DB_PATH", str(temp_root / "suggestions.db"))
    return TestClient(app)


def _scan(client: TestClient, folder: Path) -> str:
    response = client.post(
        "/localproof/scan",
        json={"folder_path": str(folder), "recursive": True, "max_files": 500},
    )
    assert response.status_code == 200
    return response.json()["case_id"]


def test_suggest_actions_creates_pending_moves_for_common_file_types(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        scan_folder = temp_root / "scan"
        scan_folder.mkdir()
        files = {
            "invoice.pdf": b"%PDF-1.4\n",
            "photo.png": b"\x89PNG\r\n\x1a\n",
            "notes.md": b"# Notes\n",
            "script.py": b"print('proof')\n",
            "run.log": b"ok\n",
        }
        for name, content in files.items():
            (scan_folder / name).write_bytes(content)

        target_root = temp_root / "sorted"

        with _client(monkeypatch, temp_root) as client:
            case_id = _scan(client, scan_folder)
            response = client.post(
                "/localproof/suggest-actions",
                json={"case_id": case_id, "target_root": str(target_root)},
            )
            assert response.status_code == 200
            summary = response.json()

            assert summary["case_id"] == case_id
            assert summary["target_root"] == str(target_root.resolve(strict=False))
            assert summary["actions_created"] == 5
            assert summary["skipped"] == 0
            assert not target_root.exists()

            actions_by_name = {
                Path(action["preview"]["from_path"]).name: action
                for action in summary["actions"]
            }
            assert set(actions_by_name) == set(files)
            assert Path(actions_by_name["invoice.pdf"]["preview"]["to_path"]).parent.name == "Documents"
            assert Path(actions_by_name["photo.png"]["preview"]["to_path"]).parent.name == "Images"
            assert Path(actions_by_name["notes.md"]["preview"]["to_path"]).parent.name == "Notes"
            assert Path(actions_by_name["script.py"]["preview"]["to_path"]).parent.name == "Code"
            assert Path(actions_by_name["run.log"]["preview"]["to_path"]).parent.name == "Logs"

            for action in summary["actions"]:
                assert action["status"] == "pending"
                assert action["kind"] == "move_file"
                assert action["result"] is None
                assert action["undo"] is None
                assert action["metadata"]["source"] == "localproof_suggest_actions"
                assert Path(action["preview"]["from_path"]).exists()
                assert not Path(action["preview"]["to_path"]).exists()

            execute_response = client.post(f"/actions/{summary['actions'][0]['id']}/execute")
            assert execute_response.status_code == 400

            approve_response = client.post(f"/actions/{summary['actions'][0]['id']}/approve")
            assert approve_response.status_code == 200
            assert approve_response.json()["status"] == "approved"

            list_response = client.get(f"/cases/{case_id}/actions")
            assert list_response.status_code == 200
            assert {action["id"] for action in list_response.json()} == {
                action["id"] for action in summary["actions"]
            }


def test_suggest_actions_uses_non_conflicting_destination_names(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        scan_folder = temp_root / "scan"
        scan_folder.mkdir()
        (scan_folder / "invoice.pdf").write_bytes(b"%PDF-1.4\n")

        target_root = temp_root / "sorted"
        documents = target_root / "Documents"
        documents.mkdir(parents=True)
        (documents / "invoice.pdf").write_text("existing", encoding="utf-8")
        (documents / "invoice-1.pdf").write_text("existing", encoding="utf-8")

        with _client(monkeypatch, temp_root) as client:
            case_id = _scan(client, scan_folder)
            response = client.post(
                "/localproof/suggest-actions",
                json={"case_id": case_id, "target_root": str(target_root)},
            )

        assert response.status_code == 200
        summary = response.json()
        assert summary["actions_created"] == 1
        destination = Path(summary["actions"][0]["preview"]["to_path"])
        assert destination.name == "invoice-2.pdf"
        assert not destination.exists()
        assert (scan_folder / "invoice.pdf").exists()
        assert (documents / "invoice.pdf").read_text(encoding="utf-8") == "existing"
        assert (documents / "invoice-1.pdf").read_text(encoding="utf-8") == "existing"


def test_suggest_actions_skips_missing_source_paths(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        scan_folder = temp_root / "scan"
        scan_folder.mkdir()
        source = scan_folder / "notes.md"
        source.write_text("# Notes\n", encoding="utf-8")

        with _client(monkeypatch, temp_root) as client:
            case_id = _scan(client, scan_folder)
            source.unlink()

            response = client.post(
                "/localproof/suggest-actions",
                json={"case_id": case_id, "target_root": str(temp_root / "sorted")},
            )

        assert response.status_code == 200
        summary = response.json()
        assert summary["actions_created"] == 0
        assert summary["skipped"] == 1
        assert summary["skipped_items"][0]["reason"] == "source_path_missing"


def test_suggest_actions_rejects_target_root_file(monkeypatch):
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        scan_folder = temp_root / "scan"
        scan_folder.mkdir()
        (scan_folder / "notes.md").write_text("# Notes\n", encoding="utf-8")
        target_root = temp_root / "not-a-directory"
        target_root.write_text("file", encoding="utf-8")

        with _client(monkeypatch, temp_root) as client:
            case_id = _scan(client, scan_folder)
            response = client.post(
                "/localproof/suggest-actions",
                json={"case_id": case_id, "target_root": str(target_root)},
            )

        assert response.status_code == 400
