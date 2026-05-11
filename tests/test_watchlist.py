import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.storage.watchlist import WatchlistStore


class WatchlistStoreTest(unittest.TestCase):
    def test_add_list_delete_watch_item(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = WatchlistStore(str(Path(tmpdir) / "watchlist.sqlite3"))
            item = store.add_item("Channel", "https://www.youtube.com/@channel", "important")

            items = store.list_items()
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].id, item.id)
            self.assertEqual(items[0].notes, "important")
            self.assertEqual(items[0].sort_order, item.sort_order)
            updated = store.update_item(item.id, "Channel 2", "https://www.youtube.com/@channel2", "updated")
            self.assertEqual(updated.name, "Channel 2")
            self.assertEqual(updated.notes, "updated")
            self.assertTrue(store.delete_item(item.id))
            self.assertEqual(store.list_items(), [])

    def test_reorder_watch_items_persists_manual_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = WatchlistStore(str(Path(tmpdir) / "watchlist.sqlite3"))
            first = store.add_item("Alpha", "https://www.youtube.com/@alpha")
            second = store.add_item("Beta", "https://www.youtube.com/@beta")
            third = store.add_item("Gamma", "https://www.youtube.com/@gamma")

            reordered = store.reorder_items([third.id, first.id, second.id])
            self.assertEqual([item.id for item in reordered], [third.id, first.id, second.id])
            self.assertEqual([item.id for item in store.list_items()], [third.id, first.id, second.id])

            with self.assertRaisesRegex(ValueError, "Unknown"):
                store.reorder_items([third.id, 9999])

    def test_reorder_watch_items_deduplicates_and_appends_trailing_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = WatchlistStore(str(Path(tmpdir) / "watchlist.sqlite3"))
            first = store.add_item("Alpha", "https://www.youtube.com/@alpha")
            second = store.add_item("Beta", "https://www.youtube.com/@beta")
            third = store.add_item("Gamma", "https://www.youtube.com/@gamma")

            reordered = store.reorder_items([third.id, third.id])

        self.assertEqual([item.id for item in reordered], [third.id, first.id, second.id])
        self.assertEqual([item.sort_order for item in reordered], [1, 2, 3])

    def test_legacy_watchlist_schema_gets_sort_order(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            database_path = Path(tmpdir) / "watchlist.sqlite3"
            with sqlite3.connect(database_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE watchlist (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        url TEXT NOT NULL,
                        notes TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "INSERT INTO watchlist (name, url, notes, created_at) VALUES (?, ?, ?, ?)",
                    ("Legacy", "https://www.youtube.com/@legacy", "", "2026-05-11T12:00:00"),
                )

            store = WatchlistStore(str(database_path))
            items = store.list_items()

        self.assertEqual(items[0].name, "Legacy")
        self.assertEqual(items[0].sort_order, items[0].id)

    def test_existing_sort_order_column_with_null_or_zero_values_is_healed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            database_path = Path(tmpdir) / "watchlist.sqlite3"
            with sqlite3.connect(database_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE watchlist (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        url TEXT NOT NULL,
                        notes TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL,
                        sort_order INTEGER
                    )
                    """
                )
                conn.execute(
                    "INSERT INTO watchlist (name, url, notes, created_at, sort_order) VALUES (?, ?, ?, ?, ?)",
                    ("Zero", "https://www.youtube.com/@zero", "", "2026-05-11T12:00:00", 0),
                )
                conn.execute(
                    "INSERT INTO watchlist (name, url, notes, created_at, sort_order) VALUES (?, ?, ?, ?, ?)",
                    ("Null", "https://www.youtube.com/@null", "", "2026-05-11T13:00:00", None),
                )

            store = WatchlistStore(str(database_path))
            items = store.list_items()

        self.assertEqual([item.name for item in items], ["Zero", "Null"])
        self.assertEqual([item.sort_order for item in items], [1, 2])


if __name__ == "__main__":
    unittest.main()
