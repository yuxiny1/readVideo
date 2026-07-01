from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, func, select, update

from backend.storage.database import Database, watchlist


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
        self.database = Database(database_path)

    def list_items(self) -> list[WatchItem]:
        statement = select(watchlist).order_by(watchlist.c.sort_order.asc(), watchlist.c.created_at.desc())
        with self.database.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_row_to_item(row) for row in rows]

    def add_item(self, name: str, url: str, notes: str = "") -> WatchItem:
        created_at = datetime.now().isoformat(timespec="seconds")
        clean_name = name.strip()
        clean_url = url.strip()
        clean_notes = notes.strip()
        with self.database.begin() as connection:
            sort_order = connection.execute(
                select(func.coalesce(func.max(watchlist.c.sort_order), 0) + 1),
            ).scalar_one()
            result = connection.execute(
                watchlist.insert().values(
                    name=clean_name,
                    url=clean_url,
                    notes=clean_notes,
                    created_at=created_at,
                    sort_order=sort_order,
                ),
            )
            item_id = int(result.inserted_primary_key[0])
        return WatchItem(item_id, clean_name, clean_url, clean_notes, created_at, sort_order)

    def delete_item(self, item_id: int) -> bool:
        with self.database.begin() as connection:
            result = connection.execute(delete(watchlist).where(watchlist.c.id == item_id))
            return result.rowcount > 0

    def update_item(self, item_id: int, name: str, url: str, notes: str = "") -> Optional[WatchItem]:
        statement = (
            update(watchlist)
            .where(watchlist.c.id == item_id)
            .values(name=name.strip(), url=url.strip(), notes=notes.strip())
        )
        with self.database.begin() as connection:
            result = connection.execute(statement)
            if result.rowcount == 0:
                return None
        return self.get_item(item_id)

    def reorder_items(self, item_ids: list[int]) -> list[WatchItem]:
        if not item_ids:
            return self.list_items()

        unique_ids = list(dict.fromkeys(item_ids))
        with self.database.begin() as connection:
            existing_ids = set(
                connection.execute(select(watchlist.c.id).where(watchlist.c.id.in_(unique_ids))).scalars().all(),
            )
            missing_ids = set(unique_ids) - existing_ids
            if missing_ids:
                raise ValueError(f"找不到以下订阅源编号：{sorted(missing_ids)}")

            for index, item_id in enumerate(unique_ids, start=1):
                connection.execute(
                    update(watchlist).where(watchlist.c.id == item_id).values(sort_order=index),
                )

            trailing = connection.execute(
                select(watchlist.c.id)
                .where(watchlist.c.id.not_in(unique_ids))
                .order_by(watchlist.c.sort_order.asc(), watchlist.c.created_at.desc()),
            ).scalars().all()
            for offset, item_id in enumerate(trailing, start=len(unique_ids) + 1):
                connection.execute(
                    update(watchlist).where(watchlist.c.id == item_id).values(sort_order=offset),
                )
        return self.list_items()

    def get_item(self, item_id: int) -> Optional[WatchItem]:
        with self.database.begin() as connection:
            row = connection.execute(
                select(watchlist).where(watchlist.c.id == item_id),
            ).mappings().first()
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
