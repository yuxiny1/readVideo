import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class TagSummary:
    id: int
    name: str
    task_count: int
    created_at: str
    updated_at: str


class TagStore:
    def __init__(self, database_path: str = "readvideo.sqlite3"):
        self.database_path = database_path
        self._ensure_schema()

    def _connect(self):
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS task_tags (
                    task_id TEXT NOT NULL,
                    tag_id INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (task_id, tag_id),
                    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_tags_task_id ON task_tags(task_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_tags_tag_id ON task_tags(tag_id)")

    def list_tags(self) -> list[TagSummary]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT tags.id, tags.name, tags.created_at, tags.updated_at,
                       COUNT(task_tags.task_id) AS task_count
                FROM tags
                LEFT JOIN task_tags ON task_tags.tag_id = tags.id
                GROUP BY tags.id
                ORDER BY tags.name COLLATE NOCASE
                """
            ).fetchall()
        return [_row_to_tag(row) for row in rows]

    def tags_for_task(self, task_id: str) -> list[str]:
        return self.tags_for_tasks([task_id]).get(task_id, [])

    def tags_for_tasks(self, task_ids: list[str]) -> dict[str, list[str]]:
        ids = [task_id for task_id in dict.fromkeys(task_ids) if task_id]
        if not ids:
            return {}
        placeholders = ",".join("?" for _ in ids)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT task_tags.task_id, tags.name
                FROM task_tags
                JOIN tags ON tags.id = task_tags.tag_id
                WHERE task_tags.task_id IN ({placeholders})
                ORDER BY tags.name COLLATE NOCASE
                """,
                ids,
            ).fetchall()
        grouped = {task_id: [] for task_id in ids}
        for row in rows:
            grouped.setdefault(row["task_id"], []).append(row["name"])
        return grouped

    def set_task_tags(self, task_id: str, tags: list[str]) -> list[str]:
        task_id = task_id.strip()
        if not task_id:
            raise ValueError("必须提供任务编号。")
        cleaned_tags = normalize_tags(tags)
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            tag_ids = []
            for name in cleaned_tags:
                conn.execute(
                    """
                    INSERT INTO tags (name, created_at, updated_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET updated_at = excluded.updated_at
                    """,
                    (name, now, now),
                )
                row = conn.execute("SELECT id FROM tags WHERE name = ? COLLATE NOCASE", (name,)).fetchone()
                tag_ids.append(row["id"])

            conn.execute("DELETE FROM task_tags WHERE task_id = ?", (task_id,))
            for tag_id in tag_ids:
                conn.execute(
                    "INSERT OR IGNORE INTO task_tags (task_id, tag_id, created_at) VALUES (?, ?, ?)",
                    (task_id, tag_id, now),
                )
            conn.execute("DELETE FROM tags WHERE id NOT IN (SELECT tag_id FROM task_tags)")
        return cleaned_tags


def normalize_tags(tags: list[str]) -> list[str]:
    cleaned = []
    seen = set()
    for tag in tags:
        name = re.sub(r"\s+", " ", str(tag).strip().lstrip("#")).strip()
        if not name:
            continue
        if len(name) > 32:
            raise ValueError("每个标签不能超过 32 个字符。")
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(name)
        if len(cleaned) >= 12:
            break
    return cleaned


def _row_to_tag(row) -> TagSummary:
    return TagSummary(
        id=row["id"],
        name=row["name"],
        task_count=row["task_count"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
