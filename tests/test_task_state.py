import unittest

from backend.core.task_state import TASKS, append_task_log, clear_tasks, set_task_status, update_task_details


class TaskStateTest(unittest.TestCase):
    def setUp(self):
        clear_tasks()

    def test_set_task_status_adds_status_log(self):
        set_task_status("task-1", "queued")
        self.assertEqual(TASKS["task-1"]["logs"][-1]["message"], "任务已进入队列。")
        set_task_status("task-1", "downloading", log_message="正在下载示例视频")

        task = TASKS["task-1"]
        self.assertEqual(task["status"], "downloading")
        self.assertEqual(task["logs"][-1]["message"], "正在下载示例视频")
        self.assertEqual(task["logs"][-1]["status"], "downloading")

    def test_update_task_details_preserves_logs(self):
        set_task_status("task-1", "downloading")
        update_task_details("task-1", download_percent=42.5)
        append_task_log("task-1", "进度接近一半")

        task = TASKS["task-1"]
        self.assertEqual(task["download_percent"], 42.5)
        self.assertEqual(task["logs"][-1]["message"], "进度接近一半")


if __name__ == "__main__":
    unittest.main()
