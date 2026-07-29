import tempfile
import unittest
from pathlib import Path

from backend.storage.history import HistoryStore, source_key_for_url


class HistoryStoreTest(unittest.TestCase):
    def test_upsert_and_list_history_record(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HistoryStore(str(Path(tmpdir) / "history.sqlite3"))
            store.upsert_task(
                {
                    "task_id": "task-1",
                    "status": "queued",
                    "url": "https://www.youtube.com/watch?v=test",
                    "created_at": "2026-05-09T10:00:00",
                    "updated_at": "2026-05-09T10:00:00",
                }
            )
            store.upsert_task(
                {
                    "task_id": "task-1",
                    "status": "completed",
                    "url": "https://www.youtube.com/watch?v=test",
                    "video_path": "downloads/video.mp4",
                    "transcription_path": "downloads/video_transcription.txt",
                    "markdown_path": "notes/video.md",
                    "created_at": "2026-05-09T10:00:00",
                    "updated_at": "2026-05-09T10:02:00",
                    "completed_at": "2026-05-09T10:02:00",
                }
            )

            records = store.list_records()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].status, "completed")
        self.assertEqual(records[0].markdown_path, "notes/video.md")

    def test_find_latest_by_url_matches_youtube_video_id(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = HistoryStore(str(Path(tmpdir) / "history.sqlite3"))
            store.upsert_task(
                {
                    "task_id": "task-1",
                    "status": "completed",
                    "url": "https://www.youtube.com/watch?v=abc123&utm_source=demo",
                    "video_path": "downloads/video.mp4",
                    "created_at": "2026-05-09T10:00:00",
                    "updated_at": "2026-05-09T10:00:00",
                }
            )

            record = store.find_latest_by_url("https://youtu.be/abc123")

        self.assertIsNotNone(record)
        self.assertEqual(record.task_id, "task-1")

    def test_bilibili_source_key_ignores_tracking_query(self):
        tracked = source_key_for_url(
            "https://www.bilibili.com/video/BV1qR3i6hETU/?spm_id_from=333.337.search-card.all.click"
        )
        clean = source_key_for_url("https://bilibili.com/video/BV1qR3i6hETU")

        self.assertEqual(tracked, "bilibili:BV1qR3i6hETU")
        self.assertEqual(tracked, clean)


if __name__ == "__main__":
    unittest.main()
