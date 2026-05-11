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
    sort_order: int


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
                    created_at TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(watchlist)").fetchall()}
            if "sort_order" not in columns:
                conn.execute("ALTER TABLE watchlist ADD COLUMN sort_order INTEGER")
                conn.execute("UPDATE watchlist SET sort_order = id WHERE sort_order IS NULL")

    def list_items(self) -> list[WatchItem]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, name, url, notes, created_at, sort_order
                FROM watchlist
                ORDER BY sort_order ASC, created_at DESC
                """
            ).fetchall()
        return [_row_to_item(row) for row in rows]

    def add_item(self, name: str, url: str, notes: str = "") -> WatchItem:
        created_at = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            sort_order = conn.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM watchlist").fetchone()[0]
            cursor = conn.execute(
                "INSERT INTO watchlist (name, url, notes, created_at, sort_order) VALUES (?, ?, ?, ?, ?)",
                (name.strip(), url.strip(), notes.strip(), created_at, sort_order),
            )
            item_id = cursor.lastrowid
        return WatchItem(item_id, name.strip(), url.strip(), notes.strip(), created_at, sort_order)

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

    def reorder_items(self, item_ids: list[int]) -> list[WatchItem]:
        if not item_ids:
            return self.list_items()

        unique_ids = []
        seen = set()
        for item_id in item_ids:
            if item_id not in seen:
                unique_ids.append(item_id)
                seen.add(item_id)

        with self._connect() as conn:
            existing_ids = {
                row["id"]
                for row in conn.execute(
                    "SELECT id FROM watchlist WHERE id IN ({})".format(",".join("?" for _ in unique_ids)),
                    tuple(unique_ids),
                ).fetchall()
            }
            missing_ids = set(unique_ids) - existing_ids
            if missing_ids:
                raise ValueError(f"Unknown watch item ids: {sorted(missing_ids)}")

            for index, item_id in enumerate(unique_ids, start=1):
                conn.execute("UPDATE watchlist SET sort_order = ? WHERE id = ?", (index, item_id))

            trailing = conn.execute(
                """
                SELECT id FROM watchlist
                WHERE id NOT IN ({})
                ORDER BY sort_order ASC, created_at DESC
                """.format(",".join("?" for _ in unique_ids)),
                tuple(unique_ids),
            ).fetchall()
            for offset, row in enumerate(trailing, start=len(unique_ids) + 1):
                conn.execute("UPDATE watchlist SET sort_order = ? WHERE id = ?", (offset, row["id"]))

        return self.list_items()

    def get_item(self, item_id: int) -> Optional[WatchItem]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, name, url, notes, created_at, sort_order FROM watchlist WHERE id = ?",
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
        sort_order=row["sort_order"],
    )
