import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api import routes
from backend.app import app
from backend.core import config
from backend.core.config import load_openai_api_key, load_settings
from backend.core.task_state import TASKS, clear_tasks, set_task_status
from backend.services.source_updates import SourceVideo
from backend.services.video_processor import build_transcription_prompt


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

    def test_load_settings_validates_local_whisper_chunk_seconds(self):
        with patch.dict(
            "os.environ",
            {"READVIDEO_TRANSCRIPTION_BACKEND": "local", "READVIDEO_LOCAL_WHISPER_CHUNK_SECONDS": "0"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "READVIDEO_LOCAL_WHISPER_CHUNK_SECONDS"):
                load_settings()

    def test_build_transcription_prompt_combines_user_terms_and_title(self):
        prompt = build_transcription_prompt("Jim Keller, CUDA", "Where AI Runs")

        self.assertEqual(prompt, "Jim Keller, CUDA. Where AI Runs")

    def test_load_settings_defaults_to_audio_downloads(self):
        with patch.dict("os.environ", {"READVIDEO_TRANSCRIPTION_BACKEND": "local"}, clear=True):
            settings = load_settings()

        self.assertEqual(settings.download_media, "audio")

    def test_load_settings_validates_download_media(self):
        with patch.dict(
            "os.environ",
            {"READVIDEO_TRANSCRIPTION_BACKEND": "local", "READVIDEO_DOWNLOAD_MEDIA": "images"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "READVIDEO_DOWNLOAD_MEDIA"):
                load_settings()

    def test_load_settings_prefers_best_installed_local_whisper_model(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            models_dir = Path(tmpdir) / "models"
            models_dir.mkdir()
            (models_dir / "ggml-small.bin").write_text("small", encoding="utf-8")
            (models_dir / "ggml-large-v3-turbo.bin").write_text("large", encoding="utf-8")

            with patch.object(config, "PROJECT_ROOT", Path(tmpdir)), patch.dict(
                "os.environ",
                {"READVIDEO_TRANSCRIPTION_BACKEND": "local"},
                clear=True,
            ):
                settings = load_settings()

        self.assertEqual(settings.local_whisper_model, "models/ggml-large-v3-turbo.bin")

    def test_load_settings_respects_explicit_local_whisper_model(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.object(config, "PROJECT_ROOT", Path(tmpdir)), patch.dict(
            "os.environ",
            {
                "READVIDEO_TRANSCRIPTION_BACKEND": "local",
                "READVIDEO_LOCAL_WHISPER_MODEL": "models/custom.bin",
            },
            clear=True,
        ):
            settings = load_settings()

        self.assertEqual(settings.local_whisper_model, "models/custom.bin")

    def test_process_video_endpoint_accepts_json_body(self):
        captured = {}

        async def fake_process_video(
            task_id,
            url,
            transcription_backend=None,
            transcription_model=None,
            transcription_prompt=None,
            local_whisper_model=None,
            local_whisper_language=None,
            notes_dir=None,
            notes_backend=None,
            ollama_model=None,
        ):
            captured.update(
                {
                    "transcription_backend": transcription_backend,
                    "transcription_model": transcription_model,
                    "transcription_prompt": transcription_prompt,
                    "local_whisper_model": local_whisper_model,
                    "local_whisper_language": local_whisper_language,
                    "notes_dir": notes_dir,
                    "notes_backend": notes_backend,
                    "ollama_model": ollama_model,
                }
            )
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
                    "transcription_backend": "local",
                    "local_whisper_model": "models/ggml-medium.bin",
                    "local_whisper_language": "auto",
                    "transcription_prompt": "Jim Keller, CUDA",
                    "notes_backend": "extractive",
                    "ollama_model": "qwen3:14b",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["task_id"], "test-task")
        self.assertEqual(TASKS["test-task"]["status"], "completed")
        self.assertEqual(captured["local_whisper_model"], "models/ggml-medium.bin")
        self.assertEqual(captured["local_whisper_language"], "auto")
        self.assertEqual(captured["transcription_prompt"], "Jim Keller, CUDA")

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

    def test_process_video_endpoint_validates_transcription_backend(self):
        with patch.dict("os.environ", {"READVIDEO_TRANSCRIPTION_BACKEND": "local"}):
            client = TestClient(app)
            response = client.post(
                "/process_video/",
                json={
                    "task_id": "test-task",
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "transcription_backend": "missing",
                },
            )

        self.assertEqual(response.status_code, 400)

    def test_process_video_endpoint_requires_key_for_openai_override(self):
        with patch.dict("os.environ", {"READVIDEO_TRANSCRIPTION_BACKEND": "local"}, clear=True):
            client = TestClient(app)
            response = client.post(
                "/process_video/",
                json={
                    "task_id": "test-task",
                    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                    "transcription_backend": "openai",
                },
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("OPENAI_API_KEY", response.json()["detail"])

    def test_index_serves_frontend(self):
        client = TestClient(app)
        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn("readVideo", response.text)
        self.assertIn("/static/js/app.js", response.text)
        self.assertIn("/history", response.text)
        self.assertIn("/favorites", response.text)
        self.assertIn("/reader", response.text)
        self.assertIn("favorite-summary", response.text)
        self.assertIn("read-summary", response.text)
        self.assertIn("watch-sort", response.text)
        self.assertIn("transcription-backend", response.text)
        self.assertIn("local-whisper-model-select", response.text)

    def test_history_page_serves_frontend(self):
        client = TestClient(app)
        response = client.get("/history")

        self.assertEqual(response.status_code, 200)
        self.assertIn("readVideo History", response.text)
        self.assertIn("/static/js/history.js", response.text)

    def test_favorites_page_serves_frontend(self):
        client = TestClient(app)
        response = client.get("/favorites")

        self.assertEqual(response.status_code, 200)
        self.assertIn("readVideo Favorites", response.text)
        self.assertIn("favorite-search", response.text)
        self.assertIn("Note Folders", response.text)
        self.assertIn("/static/js/favorites.js", response.text)

    def test_reader_page_serves_frontend(self):
        client = TestClient(app)
        response = client.get("/reader")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Markdown Reader", response.text)
        self.assertIn("reader-search", response.text)
        self.assertIn("/static/js/reader.js", response.text)

    def test_app_config_exposes_non_secret_defaults(self):
        with patch.dict("os.environ", {"READVIDEO_TRANSCRIPTION_BACKEND": "local"}, clear=True):
            client = TestClient(app)
            response = client.get("/app_config")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["transcription_backend"], "local")
        self.assertNotIn("openai_api_key", data)
        self.assertIn("ollama_model_options", data)
        self.assertEqual(data["download_media"], "audio")
        self.assertIn("local_whisper_model", data)
        self.assertEqual(data["local_whisper_language"], "auto")
        self.assertEqual(data["local_whisper_chunk_seconds"], 60)
        self.assertIn("openai_transcription_model_options", data)

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
            direct_favorite = client.post(
                "/api/favorites",
                json={"task_id": "favorite-task", "folder_id": folder["id"]},
            )
            assigned = client.patch(
                f"/api/favorites/{favorite['id']}/folder",
                json={"folder_id": folder["id"]},
            )
            markdown = client.get(f"/api/favorites/{favorite['id']}/markdown")

        self.assertEqual(assigned.status_code, 200)
        self.assertEqual(assigned.json()["folder_name"], "AI")
        self.assertEqual(direct_favorite.status_code, 200)
        self.assertEqual(direct_favorite.json()["folder_name"], "AI")
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

    def test_watchlist_endpoint_updates_saved_source(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            "os.environ",
            {"READVIDEO_DATABASE_PATH": str(Path(tmpdir) / "watchlist.sqlite3")},
            clear=True,
        ):
            client = TestClient(app)
            created = client.post(
                "/watchlist",
                json={"name": "Demo", "url": "https://www.youtube.com/@demo", "notes": ""},
            )
            response = client.patch(
                f"/watchlist/{created.json()['id']}",
                json={"name": "Updated", "url": "https://www.youtube.com/@updated", "notes": "better"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Updated")
        self.assertEqual(response.json()["notes"], "better")

    def test_watchlist_reorder_endpoint_persists_order(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            "os.environ",
            {"READVIDEO_DATABASE_PATH": str(Path(tmpdir) / "watchlist.sqlite3")},
            clear=True,
        ):
            client = TestClient(app)
            first = client.post(
                "/watchlist",
                json={"name": "First", "url": "https://www.youtube.com/@first", "notes": ""},
            ).json()
            second = client.post(
                "/watchlist",
                json={"name": "Second", "url": "https://www.youtube.com/@second", "notes": ""},
            ).json()
            response = client.patch("/watchlist/reorder", json={"item_ids": [second["id"], first["id"]]})
            listed = client.get("/watchlist")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()[:2]], [second["id"], first["id"]])
        self.assertEqual([item["id"] for item in listed.json()[:2]], [second["id"], first["id"]])

    def test_watchlist_reorder_endpoint_handles_partial_duplicate_order(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            "os.environ",
            {"READVIDEO_DATABASE_PATH": str(Path(tmpdir) / "watchlist.sqlite3")},
            clear=True,
        ):
            client = TestClient(app)
            first = client.post(
                "/watchlist",
                json={"name": "First", "url": "https://www.youtube.com/@first", "notes": ""},
            ).json()
            second = client.post(
                "/watchlist",
                json={"name": "Second", "url": "https://www.youtube.com/@second", "notes": ""},
            ).json()
            third = client.post(
                "/watchlist",
                json={"name": "Third", "url": "https://www.youtube.com/@third", "notes": ""},
            ).json()
            response = client.patch("/watchlist/reorder", json={"item_ids": [third["id"], third["id"]]})

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.json()], [third["id"], first["id"], second["id"]])
        self.assertEqual([item["sort_order"] for item in response.json()], [1, 2, 3])

    def test_watchlist_reorder_endpoint_rejects_empty_and_unknown_ids(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            "os.environ",
            {"READVIDEO_DATABASE_PATH": str(Path(tmpdir) / "watchlist.sqlite3")},
            clear=True,
        ):
            client = TestClient(app)
            created = client.post(
                "/watchlist",
                json={"name": "First", "url": "https://www.youtube.com/@first", "notes": ""},
            ).json()
            empty_response = client.patch("/watchlist/reorder", json={"item_ids": []})
            unknown_response = client.patch("/watchlist/reorder", json={"item_ids": [created["id"], 9999]})

        self.assertEqual(empty_response.status_code, 422)
        self.assertEqual(unknown_response.status_code, 404)
        self.assertIn("Unknown watch item ids", unknown_response.json()["detail"])

    def test_ollama_models_endpoint_exposes_recommendations(self):
        with patch.object(routes, "list_installed_models", return_value=["qwen2.5:3b"]):
            client = TestClient(app)
            response = client.get("/api/ollama/models")

        self.assertEqual(response.status_code, 200)
        self.assertIn("recommended", response.json())
        self.assertIn("qwen2.5:3b", response.json()["installed"])

    def test_ollama_pull_endpoint_calls_service(self):
        with patch.object(routes, "pull_model", return_value="done"):
            client = TestClient(app)
            response = client.post("/api/ollama/pull", json={"model": "qwen3:14b"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["model"], "qwen3:14b")

    def test_transcription_models_endpoint_exposes_local_and_openai_options(self):
        with patch.object(routes, "list_installed_whisper_models", return_value=["models/ggml-small.bin"]):
            client = TestClient(app)
            response = client.get("/api/transcription/models")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("whisper", data)
        self.assertIn("openai", data)
        self.assertIn("languages", data)
        self.assertIn("models/ggml-small.bin", data["installed_whisper"])

    def test_transcription_model_download_endpoint_calls_service(self):
        with patch.object(
            routes,
            "download_whisper_model",
            return_value={"model": "ggml-medium.bin", "path": "models/ggml-medium.bin", "downloaded": True},
        ):
            client = TestClient(app)
            response = client.post("/api/transcription/models/download", json={"model": "ggml-medium.bin"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["path"], "models/ggml-medium.bin")

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
