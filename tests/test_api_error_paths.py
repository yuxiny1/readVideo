import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api import routes
from backend.app import angular_index, app
from backend.core.task_state import TASKS, clear_tasks, set_task_status
from backend.storage.history import HistoryStore


class MissingAngularIndex:
    def exists(self):
        return False


class ApiErrorPathTest(unittest.TestCase):
    def setUp(self):
        clear_tasks()

    def test_reader_page_serves_frontend_and_missing_angular_build_is_503(self):
        client = TestClient(app)
        response = client.get("/reader")
        self.assertEqual(response.status_code, 200)
        self.assertIn("rv-root", response.text)

        with patch("backend.app.ANGULAR_INDEX", MissingAngularIndex()):
            missing = angular_index()
        self.assertEqual(missing.status_code, 503)

    def test_history_file_endpoint_reports_missing_records_and_files(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            "os.environ",
            {"READVIDEO_DATABASE_PATH": str(Path(tmpdir) / "history.sqlite3")},
            clear=True,
        ):
            set_task_status(
                "history-task",
                "completed",
                url="https://www.youtube.com/watch?v=abc123",
                transcription_path=str(Path(tmpdir) / "missing_transcription.txt"),
            )
            HistoryStore(str(Path(tmpdir) / "history.sqlite3")).upsert_task(TASKS["history-task"])
            client = TestClient(app)

            missing_record = client.get("/api/history/missing")
            unknown_kind = client.get("/api/history/history-task/files/summary")
            missing_file = client.get("/api/history/history-task/files/transcript")

        self.assertEqual(missing_record.status_code, 404)
        self.assertEqual(unknown_kind.status_code, 404)
        self.assertEqual(missing_file.status_code, 404)

    def test_favorite_endpoint_error_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            "os.environ",
            {"READVIDEO_DATABASE_PATH": str(Path(tmpdir) / "favorites.sqlite3")},
            clear=True,
        ):
            set_task_status(
                "empty-task",
                "completed",
                url="https://www.youtube.com/watch?v=empty",
                summary="",
                markdown_path="",
            )
            HistoryStore(str(Path(tmpdir) / "favorites.sqlite3")).upsert_task(TASKS["empty-task"])
            client = TestClient(app)

            missing_history = client.post("/api/favorites", json={"task_id": "missing"})
            no_summary = client.post("/api/favorites", json={"task_id": "empty-task"})
            folder = client.post("/api/favorites/folders", json={"name": "AI", "notes": ""})
            duplicate_folder = client.post("/api/favorites/folders", json={"name": "AI", "notes": ""})
            missing_folder_delete = client.delete("/api/favorites/folders/999")
            missing_favorite_delete = client.delete("/api/favorites/999")
            missing_assignment = client.patch("/api/favorites/999/folder", json={"folder_id": folder.json()["id"]})
            missing_markdown = client.get("/api/favorites/999/markdown")

        self.assertEqual(missing_history.status_code, 404)
        self.assertEqual(no_summary.status_code, 400)
        self.assertEqual(duplicate_folder.status_code, 400)
        self.assertEqual(missing_folder_delete.status_code, 404)
        self.assertEqual(missing_favorite_delete.status_code, 404)
        self.assertEqual(missing_assignment.status_code, 404)
        self.assertEqual(missing_markdown.status_code, 404)

    def test_markdown_file_endpoint_error_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            text_file = Path(tmpdir) / "note.txt"
            text_file.write_text("plain", encoding="utf-8")
            client = TestClient(app)

            missing_folder = client.get(f"/api/markdown_files?directory={Path(tmpdir) / 'missing'}")
            invalid_download = client.get(f"/api/markdown_files/download?path={text_file}")
            invalid_read = client.get(f"/api/markdown_files/read?path={text_file}")

        self.assertEqual(missing_folder.status_code, 404)
        self.assertEqual(invalid_download.status_code, 404)
        self.assertEqual(invalid_read.status_code, 404)

    def test_watchlist_endpoint_update_reorder_and_update_errors(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            "os.environ",
            {"READVIDEO_DATABASE_PATH": str(Path(tmpdir) / "watchlist.sqlite3")},
            clear=True,
        ):
            client = TestClient(app)
            created = client.post(
                "/watchlist",
                json={"name": "Demo", "url": "https://www.youtube.com/@demo", "notes": "watch"},
            ).json()
            updated = client.patch(
                f"/watchlist/{created['id']}",
                json={"name": "Demo 2", "url": "https://www.youtube.com/@demo2", "notes": "updated"},
            )
            missing_update = client.patch(
                "/watchlist/999",
                json={"name": "Missing", "url": "https://www.youtube.com/@missing", "notes": ""},
            )
            missing_delete = client.delete("/watchlist/999")
            missing_updates = client.get("/watchlist/999/updates")
            bad_reorder = client.patch("/watchlist/reorder", json={"item_ids": [999]})
            with patch.object(routes, "list_source_updates", side_effect=RuntimeError("yt-dlp failed")):
                failed_updates = client.get(f"/watchlist/{created['id']}/updates")

        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["name"], "Demo 2")
        self.assertEqual(missing_update.status_code, 404)
        self.assertEqual(missing_delete.status_code, 404)
        self.assertEqual(missing_updates.status_code, 404)
        self.assertEqual(bad_reorder.status_code, 404)
        self.assertEqual(failed_updates.status_code, 400)

    def test_model_management_endpoint_error_paths(self):
        with patch.dict("os.environ", {"READVIDEO_TRANSCRIPTION_BACKEND": "local"}, clear=True):
            client = TestClient(app)
            with patch.object(routes, "pull_ollama_model", side_effect=RuntimeError("api down")), patch.object(
                routes,
                "pull_model",
                return_value="installed locally",
            ):
                fallback = client.post("/api/ollama/pull", json={"model": "qwen2.5:3b"})

            with patch.object(routes, "pull_ollama_model", side_effect=RuntimeError("api down")), patch.object(
                routes,
                "pull_model",
                side_effect=RuntimeError("cli down"),
            ):
                failed_pull = client.post("/api/ollama/pull", json={"model": "qwen2.5:3b"})

            with patch.object(routes, "download_whisper_model", side_effect=ValueError("unknown model")):
                missing_whisper = client.post("/api/transcription/models/download", json={"model": "missing.bin"})

            with patch.object(routes, "download_whisper_model", side_effect=OSError("disk full")):
                failed_whisper = client.post("/api/transcription/models/download", json={"model": "ggml-base.bin"})

        self.assertEqual(fallback.status_code, 200)
        self.assertEqual(fallback.json()["result"]["output"], "installed locally")
        self.assertEqual(failed_pull.status_code, 400)
        self.assertEqual(missing_whisper.status_code, 404)
        self.assertEqual(failed_whisper.status_code, 400)


if __name__ == "__main__":
    unittest.main()
