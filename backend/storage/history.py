from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from sqlalchemy import select

from backend.storage.database import Database, dialect_insert, task_history


@dataclass(frozen=True)
class HistoryRecord:
    task_id: str
    status: str
    url: str
    title: str
    video_path: str
    transcription_path: str
    markdown_path: str
    summary: str
    error: str
    transcription_backend: str
    summary_backend: str
    created_at: str
    updated_at: str
    completed_at: Optional[str]
    source_key: str = ""


class HistoryStore:
    def __init__(self, database_path: str = "readvideo.sqlite3"):
        self.database_path = database_path
        self.database = Database(database_path)

    def upsert_task(self, task: dict[str, Any]) -> HistoryRecord:
        record = _task_to_record(task)
        values = asdict(record)
        with self.database.begin() as connection:
            statement = dialect_insert(connection, task_history).values(**values)
            statement = statement.on_conflict_do_update(
                index_elements=[task_history.c.task_id],
                set_={
                    key: statement.excluded[key]
                    for key in values
                    if key not in {"task_id", "created_at"}
                },
            )
            connection.execute(statement)
        return record

    def list_records(self, limit: int = 100) -> list[HistoryRecord]:
        statement = select(task_history).order_by(task_history.c.updated_at.desc()).limit(limit)
        with self.database.begin() as connection:
            rows = connection.execute(statement).mappings().all()
        return [_row_to_record(row) for row in rows]

    def get_record(self, task_id: str) -> Optional[HistoryRecord]:
        with self.database.begin() as connection:
            row = connection.execute(
                select(task_history).where(task_history.c.task_id == task_id),
            ).mappings().first()
        return _row_to_record(row) if row else None

    def find_latest_by_url(self, url: str) -> Optional[HistoryRecord]:
        source_key = source_key_for_url(url)
        with self.database.begin() as connection:
            if source_key:
                row = connection.execute(
                    select(task_history)
                    .where(task_history.c.source_key == source_key)
                    .order_by(task_history.c.updated_at.desc())
                    .limit(1),
                ).mappings().first()
                if row:
                    return _row_to_record(row)

            row = connection.execute(
                select(task_history)
                .where(task_history.c.url == url)
                .order_by(task_history.c.updated_at.desc())
                .limit(1),
            ).mappings().first()
            if row:
                return _row_to_record(row)

            rows = []
            if source_key:
                rows = connection.execute(
                    select(task_history)
                    .where(task_history.c.url != "")
                    .order_by(task_history.c.updated_at.desc())
                    .limit(500),
                ).mappings().all()
        for row in rows:
            if source_key_for_url(row["url"]) == source_key:
                return _row_to_record(row)
        return None


def _task_to_record(task: dict[str, Any]) -> HistoryRecord:
    video_path = str(task.get("video_path") or "")
    title = str(task.get("title") or "")
    if not title and video_path:
        title = Path(video_path).stem

    return HistoryRecord(
        task_id=str(task.get("task_id") or ""),
        status=str(task.get("status") or ""),
        url=str(task.get("url") or ""),
        source_key=str(task.get("source_key") or source_key_for_url(str(task.get("url") or ""))),
        title=title,
        video_path=video_path,
        transcription_path=str(task.get("transcription_path") or ""),
        markdown_path=str(task.get("markdown_path") or ""),
        summary=str(task.get("summary") or ""),
        error=str(task.get("error") or ""),
        transcription_backend=str(task.get("transcription_backend") or ""),
        summary_backend=str(task.get("summary_backend") or ""),
        created_at=str(task.get("created_at") or ""),
        updated_at=str(task.get("updated_at") or ""),
        completed_at=task.get("completed_at"),
    )


def _row_to_record(row) -> HistoryRecord:
    return HistoryRecord(
        task_id=row["task_id"],
        status=row["status"],
        url=row["url"],
        source_key=row["source_key"] or source_key_for_url(row["url"]),
        title=row["title"],
        video_path=row["video_path"],
        transcription_path=row["transcription_path"],
        markdown_path=row["markdown_path"],
        summary=row["summary"],
        error=row["error"],
        transcription_backend=row["transcription_backend"],
        summary_backend=row["summary_backend"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        completed_at=row["completed_at"],
    )


def source_key_for_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    path_parts = [part for part in parsed.path.split("/") if part]

    if host in {"youtube.com", "m.youtube.com", "music.youtube.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
            if video_id:
                return f"youtube:{video_id}"
        if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed", "live"}:
            return f"youtube:{path_parts[1]}"

    if host == "youtu.be" and path_parts:
        return f"youtube:{path_parts[0]}"

    normalized_path = parsed.path.rstrip("/")
    query = parsed.query
    return f"url:{host}{normalized_path}?{query}" if query else f"url:{host}{normalized_path}"
