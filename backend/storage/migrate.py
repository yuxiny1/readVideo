import argparse
from dataclasses import dataclass

from sqlalchemy import func, select, text

from backend.storage.database import (
    Database,
    dialect_insert,
    favorite_folders,
    favorite_summaries,
    tags,
    task_history,
    task_tags,
    watchlist,
)


MIGRATION_TABLES = (
    task_history,
    favorite_folders,
    favorite_summaries,
    watchlist,
    tags,
    task_tags,
)
SEQUENCE_TABLES = (favorite_folders, favorite_summaries, watchlist, tags)


@dataclass(frozen=True)
class MigrationResult:
    table_counts: dict[str, int]

    @property
    def total_rows(self) -> int:
        return sum(self.table_counts.values())


def migrate_database(source_target: str, destination_target: str) -> MigrationResult:
    source = Database(source_target, initialize=False)
    destination = Database(destination_target)
    counts: dict[str, int] = {}

    with source.begin() as source_connection, destination.begin() as destination_connection:
        for table in MIGRATION_TABLES:
            rows = source_connection.execute(select(table)).mappings().all()
            primary_keys = [column.name for column in table.primary_key.columns]
            for row in rows:
                statement = dialect_insert(destination_connection, table).values(**dict(row))
                statement = statement.on_conflict_do_nothing(index_elements=primary_keys)
                destination_connection.execute(statement)
            counts[table.name] = len(rows)

        if destination_connection.dialect.name == "postgresql":
            for table in SEQUENCE_TABLES:
                maximum_id = destination_connection.execute(
                    select(func.coalesce(func.max(table.c.id), 1)),
                ).scalar_one()
                destination_connection.execute(
                    text(
                        "SELECT setval(pg_get_serial_sequence(:table_name, 'id'), :maximum_id, true)",
                    ),
                    {"table_name": table.name, "maximum_id": maximum_id},
                )
    return MigrationResult(counts)


def main() -> None:
    parser = argparse.ArgumentParser(description="把 readVideo SQLite 数据迁移到 PostgreSQL。")
    parser.add_argument("--source", required=True, help="源 SQLite 文件路径或数据库 URL。")
    parser.add_argument("--target", required=True, help="目标 PostgreSQL 数据库 URL。")
    args = parser.parse_args()
    result = migrate_database(args.source, args.target)
    print(f"迁移完成：{result.total_rows} 行。")
    for table_name, row_count in result.table_counts.items():
        print(f"- {table_name}: {row_count}")


if __name__ == "__main__":
    main()
