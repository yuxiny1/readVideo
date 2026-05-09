import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

import main
from config import load_openai_api_key, load_settings


class MainAppTest(unittest.TestCase):
    def setUp(self):
        main.TASKS.clear()

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
        async def fake_process_video(task_id, url):
            main.set_task_status(task_id, "completed", url=url)

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}), patch.object(
            main,
            "process_video",
            fake_process_video,
        ):
            client = TestClient(main.app)
            response = client.post(
                "/process_video/",
                json={"task_id": "test-task", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["task_id"], "test-task")
        self.assertEqual(main.TASKS["test-task"]["status"], "completed")

    def test_process_video_endpoint_requires_openai_key(self):
        with patch.dict("os.environ", {}, clear=True):
            client = TestClient(main.app)
            response = client.post(
                "/process_video/",
                json={"task_id": "test-task", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            )

        self.assertEqual(response.status_code, 400)

    def test_unknown_task_returns_404(self):
        client = TestClient(main.app)
        response = client.get("/task_status/missing")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
