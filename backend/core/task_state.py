from datetime import datetime
from typing import Any


TASKS: dict[str, dict[str, Any]] = {}


def set_task_status(task_id: str, status: str, **details):
    now = datetime.now().isoformat(timespec="seconds")
    previous = TASKS.get(task_id, {})
    task = {
        **previous,
        "task_id": task_id,
        "status": status,
        "created_at": previous.get("created_at", now),
        "updated_at": now,
        **details,
    }
    if status in {"completed", "failed"}:
        task["completed_at"] = now
    TASKS[task_id] = task


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
