from datetime import datetime
from typing import Any


TASKS: dict[str, dict[str, Any]] = {}
MAX_TASK_LOGS = 120


def set_task_status(
    task_id: str,
    status: str,
    log_message: str | None = None,
    log_level: str = "info",
    **details,
):
    now = datetime.now().isoformat(timespec="seconds")
    previous = TASKS.get(task_id, {})
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
    TASKS[task_id] = task


def update_task_details(task_id: str, **details):
    now = datetime.now().isoformat(timespec="seconds")
    previous = TASKS.get(task_id, {})
    TASKS[task_id] = {
        **previous,
        "task_id": task_id,
        "created_at": previous.get("created_at", now),
        "updated_at": now,
        **details,
    }


def append_task_log(task_id: str, message: str, level: str = "info", status: str | None = None):
    now = datetime.now().isoformat(timespec="seconds")
    previous = TASKS.get(task_id, {})
    logs = _append_log(
        list(previous.get("logs") or []),
        {
            "time": now,
            "level": level,
            "status": status or previous.get("status", "queued"),
            "message": message,
        },
    )
    TASKS[task_id] = {
        **previous,
        "task_id": task_id,
        "created_at": previous.get("created_at", now),
        "updated_at": now,
        "logs": logs,
    }


def get_task(task_id: str) -> dict[str, Any] | None:
    return TASKS.get(task_id)


def list_tasks() -> list[dict[str, Any]]:
    return sorted(
        TASKS.values(),
        key=lambda task: task.get("updated_at", ""),
        reverse=True,
    )


def clear_tasks():
    TASKS.clear()


def _append_log(logs: list[dict[str, Any]], entry: dict[str, Any]) -> list[dict[str, Any]]:
    logs.append(entry)
    return logs[-MAX_TASK_LOGS:]


def _default_status_message(status: str) -> str:
    return {
        "queued": "Task queued.",
        "downloading": "Downloading video with yt-dlp.",
        "transcribing": "Transcribing audio.",
        "organizing_notes": "Writing Markdown summary and segmented notes.",
        "completed": "Task completed.",
        "failed": "Task failed.",
    }.get(status, status.replace("_", " ").capitalize())
