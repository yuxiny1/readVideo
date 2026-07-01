from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    event,
    inspect,
    text,
)
from sqlalchemy.pool import NullPool


metadata = MetaData()

task_history = Table(
    "task_history",
    metadata,
    Column("task_id", String, primary_key=True),
    Column("status", String, nullable=False),
    Column("url", Text, nullable=False, default=""),
    Column("source_key", Text, nullable=False, default=""),
    Column("title", Text, nullable=False, default=""),
    Column("video_path", Text, nullable=False, default=""),
    Column("transcription_path", Text, nullable=False, default=""),
    Column("markdown_path", Text, nullable=False, default=""),
    Column("summary", Text, nullable=False, default=""),
    Column("error", Text, nullable=False, default=""),
    Column("transcription_backend", String, nullable=False, default=""),
    Column("summary_backend", String, nullable=False, default=""),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
    Column("completed_at", String),
)
Index("idx_task_history_source_key", task_history.c.source_key)
Index("idx_task_history_url", task_history.c.url)

favorite_folders = Table(
    "favorite_folders",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String, nullable=False, unique=True),
    Column("notes", Text, nullable=False, default=""),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)

favorite_summaries = Table(
    "favorite_summaries",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("task_id", String, nullable=False, unique=True),
    Column("folder_id", Integer, ForeignKey("favorite_folders.id", ondelete="SET NULL")),
    Column("title", Text, nullable=False, default=""),
    Column("url", Text, nullable=False, default=""),
    Column("summary", Text, nullable=False, default=""),
    Column("markdown_path", Text, nullable=False, default=""),
    Column("notes_dir", Text, nullable=False, default=""),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)

watchlist = Table(
    "watchlist",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String, nullable=False),
    Column("url", Text, nullable=False),
    Column("notes", Text, nullable=False, default=""),
    Column("created_at", String, nullable=False),
    Column("sort_order", Integer, nullable=False, default=0),
)

tags = Table(
    "tags",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String, nullable=False, unique=True),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
)

task_tags = Table(
    "task_tags",
    metadata,
    Column("task_id", String, primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    Column("created_at", String, nullable=False),
)
Index("idx_task_tags_task_id", task_tags.c.task_id)
Index("idx_task_tags_tag_id", task_tags.c.tag_id)


class Database:
    def __init__(self, target: str, initialize: bool = True):
        self.target = target
        self.engine = database_engine(target)
        if initialize:
            ensure_schema(self.engine)

    @contextmanager
    def begin(self):
        with self.engine.begin() as connection:
            yield connection


def database_url(target: str) -> str:
    if "://" in target:
        return target
    path = Path(target).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


@lru_cache(maxsize=32)
def database_engine(target: str):
    url = database_url(target)
    connect_args = {"check_same_thread": False} if url.startswith("sqlite:") else {}
    pool_options = {"poolclass": NullPool} if url.startswith("sqlite:") else {}
    engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args, **pool_options)
    if url.startswith("sqlite:"):
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def ensure_schema(engine) -> None:
    metadata.create_all(engine)
    migrations = {
        "task_history": {"source_key": "TEXT NOT NULL DEFAULT ''"},
        "favorite_summaries": {"folder_id": "INTEGER"},
        "watchlist": {"sort_order": "INTEGER NOT NULL DEFAULT 0"},
    }
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table_name, columns in migrations.items():
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, definition in columns.items():
                if column_name not in existing:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))
        connection.execute(
            watchlist.update()
            .where((watchlist.c.sort_order.is_(None)) | (watchlist.c.sort_order <= 0))
            .values(sort_order=watchlist.c.id)
        )


def dialect_insert(connection, table):
    if connection.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    return insert(table)


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
