import tempfile
import unittest
from pathlib import Path

from backend.storage.favorites import FavoriteStore
from backend.storage.history import HistoryRecord


class FavoriteStoreTest(unittest.TestCase):
    def test_add_list_and_delete_favorite_from_history(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = FavoriteStore(str(Path(tmpdir) / "favorites.sqlite3"))
            favorite = store.add_from_history(
                HistoryRecord(
                    task_id="task-1",
                    status="completed",
                    url="https://www.youtube.com/watch?v=test",
                    title="Useful talk",
                    video_path="downloads/video.mp4",
                    transcription_path="downloads/video.txt",
                    markdown_path="notes/useful-talk.md",
                    summary="- Important idea",
                    error="",
                    transcription_backend="local",
                    summary_backend="extractive",
                    created_at="2026-05-09T10:00:00",
                    updated_at="2026-05-09T10:02:00",
                    completed_at="2026-05-09T10:02:00",
                )
            )

            items = store.list_items()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].id, favorite.id)
            self.assertEqual(items[0].notes_dir, "notes")
            self.assertTrue(store.delete_item(favorite.id))
            self.assertEqual(store.list_items(), [])


if __name__ == "__main__":
    unittest.main()
