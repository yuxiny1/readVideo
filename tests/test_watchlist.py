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
            self.assertTrue(store.delete_item(item.id))
            self.assertEqual(store.list_items(), [])


if __name__ == "__main__":
    unittest.main()
