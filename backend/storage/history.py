import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse


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
                CREATE TABLE IF NOT EXISTS task_history (
                    task_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    url TEXT NOT NULL DEFAULT '',
                    source_key TEXT NOT NULL DEFAULT '',
                    title TEXT NOT NULL DEFAULT '',
                    video_path TEXT NOT NULL DEFAULT '',
                    transcription_path TEXT NOT NULL DEFAULT '',
                    markdown_path TEXT NOT NULL DEFAULT '',
                    summary TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL DEFAULT '',
                    transcription_backend TEXT NOT NULL DEFAULT '',
                    summary_backend TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT
                )
                """
            )
            self._ensure_column(conn, "source_key", "TEXT NOT NULL DEFAULT ''")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_history_source_key ON task_history(source_key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_task_history_url ON task_history(url)")

    def _ensure_column(self, conn, column_name: str, column_definition: str):
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(task_history)").fetchall()}
        if column_name not in columns:
            conn.execute(f"ALTER TABLE task_history ADD COLUMN {column_name} {column_definition}")

    def upsert_task(self, task: dict[str, Any]) -> HistoryRecord:
        record = _task_to_record(task)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO task_history (
                    task_id, status, url, source_key, title, video_path, transcription_path,
                    markdown_path, summary, error, transcription_backend,
                    summary_backend, created_at, updated_at, completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    status = excluded.status,
                    url = excluded.url,
                    source_key = excluded.source_key,
                    title = excluded.title,
                    video_path = excluded.video_path,
                    transcription_path = excluded.transcription_path,
                    markdown_path = excluded.markdown_path,
                    summary = excluded.summary,
                    error = excluded.error,
                    transcription_backend = excluded.transcription_backend,
                    summary_backend = excluded.summary_backend,
                    updated_at = excluded.updated_at,
                    completed_at = excluded.completed_at
                """,
                _record_values(record),
            )
        return record

    def list_records(self, limit: int = 100) -> list[HistoryRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT task_id, status, url, title, video_path, transcription_path,
                       source_key, markdown_path, summary, error, transcription_backend,
                       summary_backend, created_at, updated_at, completed_at
                FROM task_history
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [_row_to_record(row) for row in rows]

    def get_record(self, task_id: str) -> Optional[HistoryRecord]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT task_id, status, url, title, video_path, transcription_path,
                       source_key, markdown_path, summary, error, transcription_backend,
                       summary_backend, created_at, updated_at, completed_at
                FROM task_history
                WHERE task_id = ?
                """,
                (task_id,),
            ).fetchone()
        return _row_to_record(row) if row else None

    def find_latest_by_url(self, url: str) -> Optional[HistoryRecord]:
        source_key = source_key_for_url(url)
        with self._connect() as conn:
            if source_key:
                row = conn.execute(
                    """
                    SELECT task_id, status, url, source_key, title, video_path, transcription_path,
                           markdown_path, summary, error, transcription_backend,
                           summary_backend, created_at, updated_at, completed_at
                    FROM task_history
                    WHERE source_key = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (source_key,),
                ).fetchone()
                if row:
                    return _row_to_record(row)

            row = conn.execute(
                """
                SELECT task_id, status, url, source_key, title, video_path, transcription_path,
                       markdown_path, summary, error, transcription_backend,
                       summary_backend, created_at, updated_at, completed_at
                FROM task_history
                WHERE url = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (url,),
            ).fetchone()
            if row:
                return _row_to_record(row)

            if source_key:
                rows = conn.execute(
                    """
                    SELECT task_id, status, url, source_key, title, video_path, transcription_path,
                           markdown_path, summary, error, transcription_backend,
                           summary_backend, created_at, updated_at, completed_at
                    FROM task_history
                    WHERE url != ''
                    ORDER BY updated_at DESC
                    LIMIT 500
                    """
                ).fetchall()
        for row in rows if source_key else []:
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
        source_key=row["source_key"] if "source_key" in row.keys() else source_key_for_url(row["url"]),
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


def _record_values(record: HistoryRecord) -> tuple:
    return (
        record.task_id,
        record.status,
        record.url,
        record.source_key,
        record.title,
        record.video_path,
        record.transcription_path,
        record.markdown_path,
        record.summary,
        record.error,
        record.transcription_backend,
        record.summary_backend,
        record.created_at,
        record.updated_at,
        record.completed_at,
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
