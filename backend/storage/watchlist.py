import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class WatchItem:
    id: int
    name: str
    url: str
    notes: str
    created_at: str


class WatchlistStore:
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
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
                """
            )

    def list_items(self) -> list[WatchItem]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, name, url, notes, created_at FROM watchlist ORDER BY created_at DESC"
            ).fetchall()
        return [_row_to_item(row) for row in rows]

    def add_item(self, name: str, url: str, notes: str = "") -> WatchItem:
        created_at = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO watchlist (name, url, notes, created_at) VALUES (?, ?, ?, ?)",
                (name.strip(), url.strip(), notes.strip(), created_at),
            )
            item_id = cursor.lastrowid
        return WatchItem(item_id, name.strip(), url.strip(), notes.strip(), created_at)

    def delete_item(self, item_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM watchlist WHERE id = ?", (item_id,))
            return cursor.rowcount > 0

    def update_item(self, item_id: int, name: str, url: str, notes: str = "") -> Optional[WatchItem]:
        with self._connect() as conn:
            cursor = conn.execute(
                "UPDATE watchlist SET name = ?, url = ?, notes = ? WHERE id = ?",
                (name.strip(), url.strip(), notes.strip(), item_id),
            )
            if cursor.rowcount == 0:
                return None
        return self.get_item(item_id)

    def get_item(self, item_id: int) -> Optional[WatchItem]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, name, url, notes, created_at FROM watchlist WHERE id = ?",
                (item_id,),
            ).fetchone()
        return _row_to_item(row) if row else None


def _row_to_item(row) -> WatchItem:
    return WatchItem(
        id=row["id"],
        name=row["name"],
        url=row["url"],
        notes=row["notes"],
        created_at=row["created_at"],
    )
