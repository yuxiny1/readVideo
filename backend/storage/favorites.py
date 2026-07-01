from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import delete, func, select, update

from backend.storage.database import (
    Database,
    dialect_insert,
    favorite_folders,
    favorite_summaries,
)
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
        self.database = Database(database_path)

    def list_items(self) -> list[FavoriteSummary]:
        with self.database.begin() as connection:
            rows = connection.execute(
                _favorite_select().order_by(favorite_summaries.c.updated_at.desc()),
            ).mappings().all()
        return [_row_to_favorite(row) for row in rows]

    def add_from_history(self, record: HistoryRecord, folder_id: Optional[int] = None) -> FavoriteSummary:
        now = datetime.now().isoformat(timespec="seconds")
        notes_dir = str(Path(record.markdown_path).parent) if record.markdown_path else ""
        values = {
            "task_id": record.task_id,
            "folder_id": folder_id,
            "title": record.title,
            "url": record.url,
            "summary": record.summary,
            "markdown_path": record.markdown_path,
            "notes_dir": notes_dir,
            "created_at": now,
            "updated_at": now,
        }
        with self.database.begin() as connection:
            self._validate_folder(connection, folder_id)
            statement = dialect_insert(connection, favorite_summaries).values(**values)
            statement = statement.on_conflict_do_update(
                index_elements=[favorite_summaries.c.task_id],
                set_={
                    key: statement.excluded[key]
                    for key in values
                    if key not in {"task_id", "created_at"}
                },
            )
            connection.execute(statement)
            row = connection.execute(
                _favorite_select().where(favorite_summaries.c.task_id == record.task_id),
            ).mappings().one()
        return _row_to_favorite(row)

    def get_item(self, item_id: int) -> Optional[FavoriteSummary]:
        with self.database.begin() as connection:
            row = connection.execute(
                _favorite_select().where(favorite_summaries.c.id == item_id),
            ).mappings().first()
        return _row_to_favorite(row) if row else None

    def list_folders(self) -> list[FavoriteFolder]:
        with self.database.begin() as connection:
            rows = connection.execute(
                select(favorite_folders).order_by(func.lower(favorite_folders.c.name)),
            ).mappings().all()
        return [_row_to_folder(row) for row in rows]

    def add_folder(self, name: str, notes: str = "") -> FavoriteFolder:
        now = datetime.now().isoformat(timespec="seconds")
        with self.database.begin() as connection:
            result = connection.execute(
                favorite_folders.insert().values(
                    name=name.strip(),
                    notes=notes.strip(),
                    created_at=now,
                    updated_at=now,
                ),
            )
            folder_id = int(result.inserted_primary_key[0])
            row = connection.execute(
                select(favorite_folders).where(favorite_folders.c.id == folder_id),
            ).mappings().one()
        return _row_to_folder(row)

    def update_folder(self, folder_id: int, name: str, notes: str = "") -> Optional[FavoriteFolder]:
        now = datetime.now().isoformat(timespec="seconds")
        with self.database.begin() as connection:
            result = connection.execute(
                update(favorite_folders)
                .where(favorite_folders.c.id == folder_id)
                .values(name=name.strip(), notes=notes.strip(), updated_at=now),
            )
            if result.rowcount == 0:
                return None
            row = connection.execute(
                select(favorite_folders).where(favorite_folders.c.id == folder_id),
            ).mappings().one()
        return _row_to_folder(row)

    def assign_folder(self, item_id: int, folder_id: Optional[int]) -> FavoriteSummary:
        now = datetime.now().isoformat(timespec="seconds")
        with self.database.begin() as connection:
            self._validate_folder(connection, folder_id)
            result = connection.execute(
                update(favorite_summaries)
                .where(favorite_summaries.c.id == item_id)
                .values(folder_id=folder_id, updated_at=now),
            )
            if result.rowcount == 0:
                raise ValueError("找不到收藏笔记。")
        favorite = self.get_item(item_id)
        if favorite is None:
            raise ValueError("找不到收藏笔记。")
        return favorite

    def delete_folder(self, folder_id: int) -> bool:
        with self.database.begin() as connection:
            connection.execute(
                update(favorite_summaries)
                .where(favorite_summaries.c.folder_id == folder_id)
                .values(folder_id=None),
            )
            result = connection.execute(delete(favorite_folders).where(favorite_folders.c.id == folder_id))
            return result.rowcount > 0

    def delete_item(self, item_id: int) -> bool:
        with self.database.begin() as connection:
            result = connection.execute(delete(favorite_summaries).where(favorite_summaries.c.id == item_id))
            return result.rowcount > 0

    @staticmethod
    def _validate_folder(connection, folder_id: Optional[int]) -> None:
        if folder_id is None:
            return
        exists = connection.execute(
            select(favorite_folders.c.id).where(favorite_folders.c.id == folder_id),
        ).first()
        if exists is None:
            raise ValueError("收藏文件夹不存在。")


def _favorite_select():
    return select(
        favorite_summaries,
        favorite_folders.c.name.label("folder_name"),
    ).select_from(
        favorite_summaries.outerjoin(
            favorite_folders,
            favorite_summaries.c.folder_id == favorite_folders.c.id,
        ),
    )


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
