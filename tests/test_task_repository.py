import json
import unittest
from unittest.mock import MagicMock, patch

from backend.core.task_repository import TASK_INDEX_KEY, TASK_KEY_PREFIX, TaskRepository


class TaskRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.memory = {}
        self.repository = TaskRepository(self.memory)
        self.redis = MagicMock()
        self.pipeline = MagicMock()
        self.redis.pipeline.return_value.__enter__.return_value = self.pipeline

    def test_uses_memory_without_redis(self):
        task = {"task_id": "task-1", "updated_at": "2026-01-01T00:00:00"}
        with patch.object(self.repository, "_redis_client", return_value=None):
            self.repository.save(task)
            self.assertEqual(self.repository.get("task-1"), task)
            self.assertEqual(self.repository.list(), [task])
            self.repository.clear()
        self.assertEqual(self.memory, {})

    def test_saves_and_reads_tasks_from_redis(self):
        task = {"task_id": "task-1", "updated_at": "2026-01-01T00:00:00", "title": "中文"}
        self.redis.get.return_value = json.dumps(task, ensure_ascii=False)
        with patch.object(self.repository, "_redis_client", return_value=self.redis):
            self.repository.save(task)
            loaded = self.repository.get("task-1")

        self.pipeline.set.assert_called_once()
        self.pipeline.zadd.assert_called_once()
        self.assertEqual(loaded, task)
        self.redis.get.assert_called_with(f"{TASK_KEY_PREFIX}task-1")

    def test_lists_and_clears_redis_index(self):
        task = {"task_id": "task-1", "updated_at": "2026-01-01T00:00:00"}
        self.redis.zrevrange.return_value = ["task-1"]
        self.redis.mget.return_value = [json.dumps(task)]
        self.redis.zrange.return_value = ["task-1"]
        with patch.object(self.repository, "_redis_client", return_value=self.redis):
            self.assertEqual(self.repository.list(), [task])
            self.repository.clear()

        self.redis.mget.assert_called_with([f"{TASK_KEY_PREFIX}task-1"])
        self.redis.delete.assert_any_call(f"{TASK_KEY_PREFIX}task-1")
        self.redis.delete.assert_any_call(TASK_INDEX_KEY)

    def test_prunes_expired_tasks_from_the_redis_index_and_memory(self):
        self.memory["expired"] = {"task_id": "expired"}
        self.redis.zrevrange.return_value = ["expired", "active"]
        active = {"task_id": "active", "updated_at": "2026-01-01T00:00:00"}
        self.redis.mget.return_value = [None, json.dumps(active)]

        with patch.object(self.repository, "_redis_client", return_value=self.redis):
            tasks = self.repository.list()

        self.assertEqual(tasks, [active])
        self.assertNotIn("expired", self.memory)
        self.redis.zrem.assert_called_once_with(TASK_INDEX_KEY, "expired")


if __name__ == "__main__":
    unittest.main()
