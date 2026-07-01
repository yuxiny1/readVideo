from datetime import datetime
from typing import Any

from backend.core.task_repository import TaskRepository


TASKS: dict[str, dict[str, Any]] = {}
TASK_REPOSITORY = TaskRepository(TASKS)
MAX_TASK_LOGS = 120


def set_task_status(
    task_id: str,
    status: str,
    log_message: str | None = None,
    log_level: str = "info",
    **details,
):
    now = datetime.now().isoformat(timespec="seconds")
    previous = TASK_REPOSITORY.get(task_id) or {}
    logs = list(previous.get("logs") or [])
    if log_message or previous.get("status") != status:
        logs = _append_log(
            logs,
            {
                "time": now,
                "level": log_level,
                "status": status,
                "message": log_message or _default_status_message(status),
            },
        )
    task = {
        **previous,
        "task_id": task_id,
        "status": status,
        "created_at": previous.get("created_at", now),
        "updated_at": now,
        "logs": logs,
        **details,
    }
    if status in {"completed", "failed"}:
        task["completed_at"] = now
    TASK_REPOSITORY.save(task)


def update_task_details(task_id: str, **details):
    now = datetime.now().isoformat(timespec="seconds")
    previous = TASK_REPOSITORY.get(task_id) or {}
    TASK_REPOSITORY.save({
        **previous,
        "task_id": task_id,
        "created_at": previous.get("created_at", now),
        "updated_at": now,
        **details,
    })


def append_task_log(task_id: str, message: str, level: str = "info", status: str | None = None):
    now = datetime.now().isoformat(timespec="seconds")
    previous = TASK_REPOSITORY.get(task_id) or {}
    logs = _append_log(
        list(previous.get("logs") or []),
        {
            "time": now,
            "level": level,
            "status": status or previous.get("status", "queued"),
            "message": message,
        },
    )
    TASK_REPOSITORY.save({
        **previous,
        "task_id": task_id,
        "created_at": previous.get("created_at", now),
        "updated_at": now,
        "logs": logs,
    })


def get_task(task_id: str) -> dict[str, Any] | None:
    return TASK_REPOSITORY.get(task_id)


def list_tasks() -> list[dict[str, Any]]:
    return TASK_REPOSITORY.list()


def clear_tasks():
    TASK_REPOSITORY.clear()


def _append_log(logs: list[dict[str, Any]], entry: dict[str, Any]) -> list[dict[str, Any]]:
    logs.append(entry)
    return logs[-MAX_TASK_LOGS:]


def _default_status_message(status: str) -> str:
    return {
        "queued": "任务已进入队列。",
        "downloading": "正在使用 yt-dlp 下载视频。",
        "transcribing": "正在转录音频。",
        "organizing_notes": "正在整理详细总结和分段笔记。",
        "completed": "任务已完成。",
        "failed": "任务失败。",
    }.get(status, "状态已更新。")
