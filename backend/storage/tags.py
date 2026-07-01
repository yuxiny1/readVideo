import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, select, update

from backend.storage.database import Database, dialect_insert, tags, task_tags


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
        self.database = Database(database_path)

    def list_tags(self) -> list[TagSummary]:
        statement = (
            select(
                tags.c.id,
                tags.c.name,
                tags.c.created_at,
                tags.c.updated_at,
                func.count(task_tags.c.task_id).label("task_count"),
            )
            .select_from(tags.outerjoin(task_tags, task_tags.c.tag_id == tags.c.id))
            .group_by(tags.c.id)
            .order_by(func.lower(tags.c.name))
        )
        with self.database.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_row_to_tag(row) for row in rows]

    def tags_for_task(self, task_id: str) -> list[str]:
        return self.tags_for_tasks([task_id]).get(task_id, [])

    def tags_for_tasks(self, task_ids: list[str]) -> dict[str, list[str]]:
        ids = [task_id for task_id in dict.fromkeys(task_ids) if task_id]
        if not ids:
            return {}
        statement = (
            select(task_tags.c.task_id, tags.c.name)
            .join(tags, tags.c.id == task_tags.c.tag_id)
            .where(task_tags.c.task_id.in_(ids))
            .order_by(func.lower(tags.c.name))
        )
        with self.database.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        grouped = {task_id: [] for task_id in ids}
        for row in rows:
            grouped.setdefault(row["task_id"], []).append(row["name"])
        return grouped

    def set_task_tags(self, task_id: str, tag_names: list[str]) -> list[str]:
        task_id = task_id.strip()
        if not task_id:
            raise ValueError("必须提供任务编号。")
        cleaned_tags = normalize_tags(tag_names)
        now = datetime.now().isoformat(timespec="seconds")
        with self.database.begin() as connection:
            tag_ids = []
            for name in cleaned_tags:
                row = connection.execute(
                    select(tags.c.id).where(func.lower(tags.c.name) == name.lower()),
                ).first()
                if row is None:
                    result = connection.execute(
                        tags.insert().values(name=name, created_at=now, updated_at=now),
                    )
                    tag_id = int(result.inserted_primary_key[0])
                else:
                    tag_id = int(row.id)
                    connection.execute(
                        update(tags).where(tags.c.id == tag_id).values(updated_at=now),
                    )
                tag_ids.append(tag_id)

            connection.execute(delete(task_tags).where(task_tags.c.task_id == task_id))
            for tag_id in tag_ids:
                statement = dialect_insert(connection, task_tags).values(
                    task_id=task_id,
                    tag_id=tag_id,
                    created_at=now,
                )
                connection.execute(statement.on_conflict_do_nothing())
            connection.execute(
                delete(tags).where(tags.c.id.not_in(select(task_tags.c.tag_id))),
            )
        return cleaned_tags


def normalize_tags(tag_names: list[str]) -> list[str]:
    cleaned = []
    seen = set()
    for tag in tag_names:
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
