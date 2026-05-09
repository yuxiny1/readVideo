import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.api import routes
from backend.app import app
from backend.core.config import load_openai_api_key, load_settings
from backend.core.task_state import TASKS, clear_tasks, set_task_status


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
        ):
            set_task_status(task_id, "completed", url=url)

        with patch.dict("os.environ", {"READVIDEO_TRANSCRIPTION_BACKEND": "local"}), patch.object(
            routes,
            "process_video",
            fake_process_video,
        ):
            client = TestClient(app)
            response = client.post(
                "/process_video/",
                json={"task_id": "test-task", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
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
        self.assertIn("readVideo", response.text)
        self.assertIn("/static/js/app.js", response.text)

    def test_app_config_exposes_non_secret_defaults(self):
        with patch.dict("os.environ", {"READVIDEO_TRANSCRIPTION_BACKEND": "local"}, clear=True):
            client = TestClient(app)
            response = client.get("/app_config")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["transcription_backend"], "local")
        self.assertNotIn("openai_api_key", data)

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
