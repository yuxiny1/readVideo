import tempfile
import unittest
from pathlib import Path

from backend.storage.favorites import FavoriteStore
from backend.storage.history import HistoryStore
from backend.storage.migrate import migrate_database
from backend.storage.tags import TagStore
from backend.storage.watchlist import WatchlistStore


class DatabaseMigrationTest(unittest.TestCase):
    def test_migrates_all_storage_domains_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = str(Path(tmpdir) / "source.sqlite3")
            target = str(Path(tmpdir) / "target.sqlite3")
            history = HistoryStore(source)
            history.upsert_task(
                {
                    "task_id": "task-1",
                    "status": "completed",
                    "url": "https://example.com/video",
                    "title": "示例",
                    "created_at": "2026-01-01T00:00:00",
                    "updated_at": "2026-01-01T00:01:00",
                },
            )
            folder = FavoriteStore(source).add_folder("课程")
            FavoriteStore(source).add_from_history(history.get_record("task-1"), folder.id)
            WatchlistStore(source).add_item("频道", "https://example.com/channel")
            TagStore(source).set_task_tags("task-1", ["课程"])

            first = migrate_database(source, target)
            second = migrate_database(source, target)

            self.assertGreaterEqual(first.total_rows, 5)
            self.assertEqual(second.table_counts, first.table_counts)
            self.assertEqual(len(HistoryStore(target).list_records()), 1)
            self.assertEqual(len(FavoriteStore(target).list_items()), 1)
            self.assertEqual(len(WatchlistStore(target).list_items()), 1)
            self.assertEqual(TagStore(target).tags_for_task("task-1"), ["课程"])


if __name__ == "__main__":
    unittest.main()
