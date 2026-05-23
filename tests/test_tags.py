import tempfile
import unittest
from pathlib import Path

from backend.storage.tags import TagStore, normalize_tags


class TagStoreTest(unittest.TestCase):
    def test_normalize_tags_strips_hashes_whitespace_and_duplicates(self):
        tags = normalize_tags([" #AI ", "ai", "course notes", "", "  local   llm  "])

        self.assertEqual(tags, ["AI", "course notes", "local llm"])

    def test_set_task_tags_replaces_tags_and_counts_usage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = TagStore(str(Path(tmpdir) / "tags.sqlite3"))

            self.assertEqual(store.set_task_tags("task-1", ["AI", "course", "AI"]), ["AI", "course"])
            store.set_task_tags("task-2", ["AI"])
            tags = store.list_tags()

            self.assertEqual(store.tags_for_task("task-1"), ["AI", "course"])
            self.assertEqual({tag.name: tag.task_count for tag in tags}, {"AI": 2, "course": 1})

            store.set_task_tags("task-1", ["reader"])

            self.assertEqual(store.tags_for_task("task-1"), ["reader"])
            self.assertEqual({tag.name: tag.task_count for tag in store.list_tags()}, {"AI": 1, "reader": 1})


if __name__ == "__main__":
    unittest.main()
