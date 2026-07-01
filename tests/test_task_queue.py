import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.core.config import Settings
from backend.services.task_queue import enqueue_video_processing, run_video_job


class TaskQueueTest(unittest.TestCase):
    def test_local_mode_uses_fastapi_background_tasks(self):
        background_tasks = MagicMock()
        processor = MagicMock()

        backend = enqueue_video_processing(background_tasks, processor, Settings(), "task-1", "url")

        self.assertEqual(backend, "local")
        background_tasks.add_task.assert_called_once_with(processor, "task-1", "url")

    def test_redis_mode_enqueues_worker_job(self):
        background_tasks = MagicMock()
        processor = MagicMock()
        queue = MagicMock()
        with patch("redis.Redis.from_url", return_value=MagicMock()), patch("rq.Queue", return_value=queue):
            backend = enqueue_video_processing(
                background_tasks,
                processor,
                Settings(redis_url="redis://redis:6379/0"),
                "task-1",
                "url",
            )

        self.assertEqual(backend, "redis")
        background_tasks.add_task.assert_not_called()
        queue.enqueue.assert_called_once()
        self.assertEqual(queue.enqueue.call_args.kwargs["job_id"], "task-1")

    def test_worker_runs_async_video_processor(self):
        processor = AsyncMock()
        with patch("backend.services.video_processor.process_video", processor):
            run_video_job("task-1", "url")
        processor.assert_awaited_once_with("task-1", "url")


if __name__ == "__main__":
    unittest.main()
