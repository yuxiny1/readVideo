import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.storage.history import HistoryRecord


@dataclass(frozen=True)
class FavoriteSummary:
    id: int
    task_id: str
    title: str
    url: str
    summary: str
    markdown_path: str
    notes_dir: str
    created_at: str
    updated_at: str


class FavoriteStore:
    def __init__(self, database_path: str = "readvideo.sqlite3"):
        self.database_path = database_path
        self._ensure_schema()

    def _connect(self):
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS favorite_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL DEFAULT '',
                    url TEXT NOT NULL DEFAULT '',
                    summary TEXT NOT NULL DEFAULT '',
                    markdown_path TEXT NOT NULL DEFAULT '',
                    notes_dir TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def list_items(self) -> list[FavoriteSummary]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, task_id, title, url, summary, markdown_path,
                       notes_dir, created_at, updated_at
                FROM favorite_summaries
                ORDER BY updated_at DESC
                """
            ).fetchall()
        return [_row_to_favorite(row) for row in rows]

    def add_from_history(self, record: HistoryRecord) -> FavoriteSummary:
        now = datetime.now().isoformat(timespec="seconds")
        notes_dir = str(Path(record.markdown_path).parent) if record.markdown_path else ""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO favorite_summaries (
                    task_id, title, url, summary, markdown_path, notes_dir,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    title = excluded.title,
                    url = excluded.url,
                    summary = excluded.summary,
                    markdown_path = excluded.markdown_path,
                    notes_dir = excluded.notes_dir,
                    updated_at = excluded.updated_at
                """,
                (
                    record.task_id,
                    record.title,
                    record.url,
                    record.summary,
                    record.markdown_path,
                    notes_dir,
                    now,
                    now,
                ),
            )
            row = conn.execute(
                """
                SELECT id, task_id, title, url, summary, markdown_path,
                       notes_dir, created_at, updated_at
                FROM favorite_summaries
                WHERE task_id = ?
                """,
                (record.task_id,),
            ).fetchone()
        return _row_to_favorite(row)

    def get_item(self, item_id: int) -> Optional[FavoriteSummary]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, task_id, title, url, summary, markdown_path,
                       notes_dir, created_at, updated_at
                FROM favorite_summaries
                WHERE id = ?
                """,
                (item_id,),
            ).fetchone()
        return _row_to_favorite(row) if row else None

    def delete_item(self, item_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM favorite_summaries WHERE id = ?", (item_id,))
            return cursor.rowcount > 0


def _row_to_favorite(row) -> FavoriteSummary:
    return FavoriteSummary(
        id=row["id"],
        task_id=row["task_id"],
        title=row["title"],
        url=row["url"],
        summary=row["summary"],
        markdown_path=row["markdown_path"],
        notes_dir=row["notes_dir"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
