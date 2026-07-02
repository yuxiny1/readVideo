from pathlib import Path

from backend.application.errors import ApplicationError
from backend.application.handlers.dependencies import tag_store
from backend.application.messages.reader import (
    ListMarkdownFilesQuery,
    ListTagsQuery,
    ReadMarkdownQuery,
    ResolveMarkdownDownloadQuery,
)
from backend.core.config import load_settings
from backend.services.markdown_files import list_markdown_files, read_markdown_file, resolve_markdown_file


class ListMarkdownFilesHandler:
    def handle(self, query: ListMarkdownFilesQuery) -> list[dict]:
        settings = load_settings()
        try:
            files = list_markdown_files(query.directory or settings.notes_dir, settings.notes_dir)
        except (FileNotFoundError, NotADirectoryError) as exc:
            raise ApplicationError(404, str(exc)) from exc
        return [item.__dict__ for item in files]


class ReadMarkdownHandler:
    def handle(self, query: ReadMarkdownQuery) -> dict:
        try:
            document = read_markdown_file(query.path, load_settings().notes_dir)
        except (FileNotFoundError, ValueError, UnicodeDecodeError) as exc:
            raise ApplicationError(404, str(exc)) from exc
        return document.__dict__


class ResolveMarkdownDownloadHandler:
    def handle(self, query: ResolveMarkdownDownloadQuery) -> Path:
        try:
            return resolve_markdown_file(query.path, load_settings().notes_dir)
        except (FileNotFoundError, ValueError) as exc:
            raise ApplicationError(404, str(exc)) from exc


class ListTagsHandler:
    def handle(self, _query: ListTagsQuery) -> list[dict]:
        return [tag.__dict__ for tag in tag_store().list_tags()]
