import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api import routes
from backend.app import app
from backend.core.config import load_openai_api_key, load_settings
from backend.core.task_state import TASKS, clear_tasks, set_task_status
from backend.services.source_updates import SourceVideo


class MainAppTest(unittest.TestCase):
    def setUp(self):
        clear_tasks()

    def test_load_openai_api_key_prefers_environment(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "env-key"}):
            self.assertEqual(load_openai_api_key("missing.json"), "env-key")

    def test_load_openai_api_key_reads_legacy_json_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            key_path = Path(tmpdir) / "apiKey.json"
            key_path.write_text(json.dumps({"apiKey": "file-key"}), encoding="utf-8")

            with patch.dict("os.environ", {}, clear=True):
                self.assertEqual(load_openai_api_key(str(key_path)), "file-key")

    def test_load_settings_validates_chunk_seconds(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key", "READVIDEO_CHUNK_SECONDS": "0"}):
            with self.assertRaisesRegex(RuntimeError, "greater than 0"):
                load_settings()

    def test_process_video_endpoint_accepts_json_body(self):
        async def fake_process_video(
            task_id,
            url,
            notes_dir=None,
            notes_backend=None,
            ollama_model=None,
            reuse_task_id=None,
            force_download=False,
            delete_video_after_completion=False,
            transcription_backend=None,
            transcription_model=None,
            transcription_prompt=None,
            local_whisper_model=None,
            local_whisper_language=None,
        ):
            self.assertTrue(delete_video_after_completion)
            set_task_status(task_id, "completed", url=url)

        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            "os.environ",
            {
                "READVIDEO_TRANSCRIPTION_BACKEND": "local",
                "READVIDEO_DATABASE_PATH": str(Path(tmpdir) / "history.sqlite3"),
            },
        ), patch.object(routes, "process_video", fake_process_video):
            client = TestClient(app)
            response = client.post(
                "/process_video/",
                json={
                    "task_id": "test-task",
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "delete_video_after_completion": True,
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["task_id"], "test-task")
        self.assertEqual(TASKS["test-task"]["status"], "completed")

    def test_process_video_endpoint_validates_notes_backend(self):
        with patch.dict("os.environ", {"READVIDEO_TRANSCRIPTION_BACKEND": "local"}):
            client = TestClient(app)
            response = client.post(
                "/process_video/",
                json={
                    "task_id": "test-task",
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "notes_backend": "missing",
                },
            )

        self.assertEqual(response.status_code, 400)

    def test_index_serves_frontend(self):
        client = TestClient(app)
        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("rv-root", response.text)

    def test_history_page_serves_frontend(self):
        client = TestClient(app)
        response = client.get("/history")

        self.assertEqual(response.status_code, 200)
        self.assertIn("rv-root", response.text)

    def test_favorites_page_serves_frontend(self):
        client = TestClient(app)
        response = client.get("/favorites")

        self.assertEqual(response.status_code, 200)
        self.assertIn("rv-root", response.text)

    def test_app_config_exposes_non_secret_defaults(self):
        with patch.dict("os.environ", {"READVIDEO_TRANSCRIPTION_BACKEND": "local"}, clear=True):
            client = TestClient(app)
            response = client.get("/app_config")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["transcription_backend"], "local")
        self.assertNotIn("openai_api_key", data)

    def test_ollama_models_endpoint_lists_installed_models(self):
        model = SimpleNamespace(
            name="qwen2.5:3b",
            size=1929912432,
            size_label="1.8 GB",
            modified_at="2026-05-11T08:25:06+01:00",
            family="qwen2",
            parameter_size="3.1B",
            quantization_level="Q4_K_M",
        )
        with patch.dict("os.environ", {"READVIDEO_TRANSCRIPTION_BACKEND": "local"}, clear=True), patch.object(
            routes,
            "list_ollama_models",
            return_value=[model],
        ):
            client = TestClient(app)
            response = client.get("/api/ollama/models")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["models"][0]["name"], "qwen2.5:3b")

    def test_ollama_models_endpoint_reports_connection_error(self):
        with patch.dict("os.environ", {"READVIDEO_TRANSCRIPTION_BACKEND": "local"}, clear=True), patch.object(
            routes,
            "list_ollama_models",
            side_effect=RuntimeError("Could not reach Ollama."),
        ):
            client = TestClient(app)
            response = client.get("/api/ollama/models")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "error")

    def test_transcription_models_endpoint_lists_recommended_whisper(self):
        with patch.dict("os.environ", {"READVIDEO_TRANSCRIPTION_BACKEND": "local"}, clear=True):
            client = TestClient(app)
            response = client.get("/api/transcription/models")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        recommended = [model for model in data["whisper"] if model["recommended"]]
        self.assertEqual(recommended[0]["name"], "ggml-large-v3-turbo.bin")
        self.assertIn("auto", [language["code"] for language in data["languages"]])

    def test_tasks_endpoint_lists_recent_task_metadata(self):
        set_task_status("task-1", "queued", url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        set_task_status("task-1", "completed", markdown_path="notes/demo.md")

        client = TestClient(app)
        response = client.get("/tasks")

        self.assertEqual(response.status_code, 200)
        task = response.json()[0]
        self.assertEqual(task["task_id"], "task-1")
        self.assertEqual(task["status"], "completed")
        self.assertIn("created_at", task)
        self.assertIn("updated_at", task)
        self.assertIn("completed_at", task)

    def test_history_endpoint_lists_persisted_records(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            "os.environ",
            {"READVIDEO_DATABASE_PATH": str(Path(tmpdir) / "history.sqlite3")},
            clear=True,
        ):
            set_task_status(
                "history-task",
                "completed",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                video_path="downloads/video.mp4",
                transcription_path="downloads/video_transcription.txt",
                markdown_path="notes/video.md",
            )
            queued_task = TASKS["history-task"]
            from backend.storage.history import HistoryStore

            HistoryStore(str(Path(tmpdir) / "history.sqlite3")).upsert_task(queued_task)
            client = TestClient(app)
            response = client.get("/api/history")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["task_id"], "history-task")
        self.assertEqual(response.json()[0]["markdown_path"], "notes/video.md")

    def test_history_lookup_reports_reusable_local_files(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            "os.environ",
            {"READVIDEO_DATABASE_PATH": str(Path(tmpdir) / "history.sqlite3")},
            clear=True,
        ):
            video = Path(tmpdir) / "video.mp4"
            transcript = Path(tmpdir) / "video_transcription.txt"
            video.write_text("video", encoding="utf-8")
            transcript.write_text("transcript", encoding="utf-8")
            set_task_status(
                "history-task",
                "completed",
                url="https://www.youtube.com/watch?v=abc123",
                video_path=str(video),
                transcription_path=str(transcript),
                summary="- saved",
            )
            from backend.storage.history import HistoryStore

            HistoryStore(str(Path(tmpdir) / "history.sqlite3")).upsert_task(TASKS["history-task"])
            client = TestClient(app)
            response = client.get("/api/history/lookup?url=https://youtu.be/abc123")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["can_reuse"])
        self.assertTrue(response.json()["transcript_exists"])

    def test_history_file_endpoint_downloads_task_output(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            "os.environ",
            {"READVIDEO_DATABASE_PATH": str(Path(tmpdir) / "history.sqlite3")},
            clear=True,
        ):
            transcript = Path(tmpdir) / "video_transcription.txt"
            transcript.write_text("hello transcript", encoding="utf-8")
            set_task_status(
                "file-task",
                "completed",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                transcription_path=str(transcript),
            )
            from backend.storage.history import HistoryStore

            HistoryStore(str(Path(tmpdir) / "history.sqlite3")).upsert_task(TASKS["file-task"])
            client = TestClient(app)
            response = client.get("/api/history/file-task/files/transcript")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "hello transcript")

    def test_favorites_endpoint_adds_history_record(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            "os.environ",
            {"READVIDEO_DATABASE_PATH": str(Path(tmpdir) / "history.sqlite3")},
            clear=True,
        ):
            set_task_status(
                "favorite-task",
                "completed",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                title="Favorite video",
                markdown_path="notes/favorite-video.md",
                summary="- useful",
            )
            from backend.storage.history import HistoryStore

            HistoryStore(str(Path(tmpdir) / "history.sqlite3")).upsert_task(TASKS["favorite-task"])
            client = TestClient(app)
            response = client.post("/api/favorites", json={"task_id": "favorite-task"})
            list_response = client.get("/api/favorites")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["notes_dir"], "notes")
        self.assertEqual(list_response.json()[0]["task_id"], "favorite-task")

    def test_favorite_folders_endpoint_assigns_favorite(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            "os.environ",
            {"READVIDEO_DATABASE_PATH": str(Path(tmpdir) / "history.sqlite3")},
            clear=True,
        ):
            note = Path(tmpdir) / "favorite-video.md"
            note.write_text("# Favorite\n\nBody", encoding="utf-8")
            set_task_status(
                "favorite-task",
                "completed",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                title="Favorite video",
                markdown_path=str(note),
                summary="- useful",
            )
            from backend.storage.history import HistoryStore

            HistoryStore(str(Path(tmpdir) / "history.sqlite3")).upsert_task(TASKS["favorite-task"])
            client = TestClient(app)
            favorite = client.post("/api/favorites", json={"task_id": "favorite-task"}).json()
            folder = client.post("/api/favorites/folders", json={"name": "AI", "notes": "models"}).json()
            assigned = client.patch(
                f"/api/favorites/{favorite['id']}/folder",
                json={"folder_id": folder["id"]},
            )
            markdown = client.get(f"/api/favorites/{favorite['id']}/markdown")

        self.assertEqual(assigned.status_code, 200)
        self.assertEqual(assigned.json()["folder_name"], "AI")
        self.assertEqual(markdown.status_code, 200)
        self.assertEqual(markdown.json()["content"], "# Favorite\n\nBody")

    def test_markdown_files_endpoint_lists_and_downloads_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            note = Path(tmpdir) / "note.md"
            note.write_text("# Note", encoding="utf-8")
            client = TestClient(app)
            list_response = client.get(f"/api/markdown_files?directory={tmpdir}")
            download_response = client.get(f"/api/markdown_files/download?path={note}")
            read_response = client.get(f"/api/markdown_files/read?path={note}")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()[0]["name"], "note.md")
        self.assertEqual(download_response.status_code, 200)
        self.assertEqual(download_response.text, "# Note")
        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(read_response.json()["content"], "# Note")

    def test_watchlist_updates_endpoint_uses_saved_source(self):
        updates = [
            SourceVideo(
                title="Latest",
                url="https://www.youtube.com/watch?v=abc123",
                video_id="abc123",
                uploader="Demo",
                upload_date="20260509",
                duration=120,
            )
        ]
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            "os.environ",
            {"READVIDEO_DATABASE_PATH": str(Path(tmpdir) / "watchlist.sqlite3")},
            clear=True,
        ), patch.object(routes, "list_source_updates", return_value=updates):
            client = TestClient(app)
            created = client.post(
                "/watchlist",
                json={"name": "Demo", "url": "https://www.youtube.com/@demo", "notes": ""},
            )
            response = client.get(f"/watchlist/{created.json()['id']}/updates?limit=1")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["updates"][0]["title"], "Latest")

    def test_openai_backend_requires_openai_key(self):
        with patch.dict("os.environ", {"READVIDEO_TRANSCRIPTION_BACKEND": "openai"}, clear=True):
            client = TestClient(app)
            response = client.post(
                "/process_video/",
                json={"task_id": "test-task", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            )

        self.assertEqual(response.status_code, 400)

    def test_local_backend_does_not_require_openai_key(self):
        with patch.dict("os.environ", {"READVIDEO_TRANSCRIPTION_BACKEND": "local"}, clear=True):
            settings = load_settings()

        self.assertEqual(settings.transcription_backend, "local")
        self.assertIsNone(settings.openai_api_key)

    def test_unknown_task_returns_404(self):
        client = TestClient(app)
        response = client.get("/task_status/missing")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
