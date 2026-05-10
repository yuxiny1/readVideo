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
    folder_id: Optional[int]
    folder_name: str
    title: str
    url: str
    summary: str
    markdown_path: str
    notes_dir: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class FavoriteFolder:
    id: int
    name: str
    notes: str
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
                CREATE TABLE IF NOT EXISTS favorite_folders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS favorite_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL UNIQUE,
                    folder_id INTEGER,
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
            self._ensure_column(conn, "favorite_summaries", "folder_id", "INTEGER")

    def list_items(self) -> list[FavoriteSummary]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT fs.id, fs.task_id, fs.folder_id, ff.name AS folder_name,
                       fs.title, fs.url, fs.summary, fs.markdown_path,
                       fs.notes_dir, fs.created_at, fs.updated_at
                FROM favorite_summaries fs
                LEFT JOIN favorite_folders ff ON fs.folder_id = ff.id
                ORDER BY fs.updated_at DESC
                """
            ).fetchall()
        return [_row_to_favorite(row) for row in rows]

    def add_from_history(self, record: HistoryRecord, folder_id: Optional[int] = None) -> FavoriteSummary:
        now = datetime.now().isoformat(timespec="seconds")
        notes_dir = str(Path(record.markdown_path).parent) if record.markdown_path else ""
        with self._connect() as conn:
            if folder_id is not None:
                folder = conn.execute("SELECT id FROM favorite_folders WHERE id = ?", (folder_id,)).fetchone()
                if folder is None:
                    raise ValueError("Favorite folder does not exist.")

            conn.execute(
                """
                INSERT INTO favorite_summaries (
                    task_id, folder_id, title, url, summary, markdown_path, notes_dir,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    folder_id = excluded.folder_id,
                    title = excluded.title,
                    url = excluded.url,
                    summary = excluded.summary,
                    markdown_path = excluded.markdown_path,
                    notes_dir = excluded.notes_dir,
                    updated_at = excluded.updated_at
                """,
                (
                    record.task_id,
                    folder_id,
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
                SELECT fs.id, fs.task_id, fs.folder_id, ff.name AS folder_name,
                       fs.title, fs.url, fs.summary, fs.markdown_path,
                       fs.notes_dir, fs.created_at, fs.updated_at
                FROM favorite_summaries fs
                LEFT JOIN favorite_folders ff ON fs.folder_id = ff.id
                WHERE fs.task_id = ?
                """,
                (record.task_id,),
            ).fetchone()
        return _row_to_favorite(row)

    def get_item(self, item_id: int) -> Optional[FavoriteSummary]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT fs.id, fs.task_id, fs.folder_id, ff.name AS folder_name,
                       fs.title, fs.url, fs.summary, fs.markdown_path,
                       fs.notes_dir, fs.created_at, fs.updated_at
                FROM favorite_summaries fs
                LEFT JOIN favorite_folders ff ON fs.folder_id = ff.id
                WHERE fs.id = ?
                """,
                (item_id,),
            ).fetchone()
        return _row_to_favorite(row) if row else None

    def list_folders(self) -> list[FavoriteFolder]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, notes, created_at, updated_at
                FROM favorite_folders
                ORDER BY name COLLATE NOCASE
                """
            ).fetchall()
        return [_row_to_folder(row) for row in rows]

    def add_folder(self, name: str, notes: str = "") -> FavoriteFolder:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO favorite_folders (name, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (name.strip(), notes.strip(), now, now),
            )
            folder_id = cursor.lastrowid
            row = conn.execute(
                "SELECT id, name, notes, created_at, updated_at FROM favorite_folders WHERE id = ?",
                (folder_id,),
            ).fetchone()
        return _row_to_folder(row)

    def assign_folder(self, item_id: int, folder_id: Optional[int]) -> FavoriteSummary:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            if folder_id is not None:
                folder = conn.execute("SELECT id FROM favorite_folders WHERE id = ?", (folder_id,)).fetchone()
                if folder is None:
                    raise ValueError("Favorite folder does not exist.")

            cursor = conn.execute(
                "UPDATE favorite_summaries SET folder_id = ?, updated_at = ? WHERE id = ?",
                (folder_id, now, item_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("Favorite not found.")
        favorite = self.get_item(item_id)
        if favorite is None:
            raise ValueError("Favorite not found.")
        return favorite

    def delete_folder(self, folder_id: int) -> bool:
        with self._connect() as conn:
            conn.execute("UPDATE favorite_summaries SET folder_id = NULL WHERE folder_id = ?", (folder_id,))
            cursor = conn.execute("DELETE FROM favorite_folders WHERE id = ?", (folder_id,))
            return cursor.rowcount > 0

    def delete_item(self, item_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM favorite_summaries WHERE id = ?", (item_id,))
            return cursor.rowcount > 0

    @staticmethod
    def _ensure_column(conn, table_name: str, column_name: str, definition: str):
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
        if column_name not in {row["name"] for row in rows}:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _row_to_favorite(row) -> FavoriteSummary:
    return FavoriteSummary(
        id=row["id"],
        task_id=row["task_id"],
        folder_id=row["folder_id"],
        folder_name=row["folder_name"] or "",
        title=row["title"],
        url=row["url"],
        summary=row["summary"],
        markdown_path=row["markdown_path"],
        notes_dir=row["notes_dir"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def _row_to_folder(row) -> FavoriteFolder:
    return FavoriteFolder(
        id=row["id"],
        name=row["name"],
        notes=row["notes"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
