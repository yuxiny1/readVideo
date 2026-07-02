from pathlib import Path

from backend.application.errors import ApplicationError
from backend.application.handlers.dependencies import (
    favorite_dict,
    favorite_store,
    history_record_dict,
    history_store,
    tag_store,
)
from backend.application.messages.library import (
    AssignFavoriteFolderCommand,
    CreateFavoriteCommand,
    CreateFavoriteFolderCommand,
    DeleteFavoriteCommand,
    DeleteFavoriteFolderCommand,
    GetHistoryFileQuery,
    GetHistoryQuery,
    ListFavoriteFoldersQuery,
    ListFavoritesQuery,
    ListHistoryQuery,
    LookupHistoryQuery,
    ReadFavoriteMarkdownQuery,
    UpdateFavoriteFolderCommand,
    UpdateFavoriteTagsCommand,
    UpdateHistoryTagsCommand,
)
from backend.core.config import load_settings
from backend.services.history_reuse import find_history_reuse_candidate
from backend.services.markdown_files import read_markdown_file, resolve_markdown_file


class ListHistoryHandler:
    def handle(self, _query: ListHistoryQuery) -> list[dict]:
        records = history_store().list_records()
        tags_by_task = tag_store().tags_for_tasks([record.task_id for record in records])
        return [history_record_dict(record, tags_by_task.get(record.task_id, [])) for record in records]


class LookupHistoryHandler:
    def handle(self, query: LookupHistoryQuery) -> dict:
        settings = load_settings()
        candidate = find_history_reuse_candidate(settings.database_path, query.url, settings.download_dir)
        if candidate is None:
            return {"found": False, "can_reuse": False}
        record = candidate.record
        return {
            "found": True,
            "can_reuse": candidate.can_reuse,
            "video_exists": candidate.video_exists,
            "transcript_exists": candidate.transcript_exists,
            "markdown_exists": candidate.markdown_exists,
            "record": history_record_dict(record, tag_store().tags_for_task(record.task_id)),
            "resolved_paths": {
                "video": str(candidate.video_path) if candidate.video_path else "",
                "transcript": str(candidate.transcript_path) if candidate.transcript_path else "",
                "markdown": str(candidate.markdown_path) if candidate.markdown_path else "",
            },
        }


class GetHistoryHandler:
    def handle(self, query: GetHistoryQuery) -> dict:
        record = history_store().get_record(query.task_id)
        if record is None:
            raise ApplicationError(404, "找不到历史记录。")
        return history_record_dict(record, tag_store().tags_for_task(record.task_id))


class UpdateHistoryTagsHandler:
    def handle(self, command: UpdateHistoryTagsCommand) -> dict:
        record = history_store().get_record(command.task_id)
        if record is None:
            raise ApplicationError(404, "找不到历史记录。")
        try:
            tags = tag_store().set_task_tags(command.task_id, command.tags)
        except ValueError as exc:
            raise ApplicationError(400, str(exc)) from exc
        return history_record_dict(record, tags)


class GetHistoryFileHandler:
    def handle(self, query: GetHistoryFileQuery) -> Path:
        record = history_store().get_record(query.task_id)
        if record is None:
            raise ApplicationError(404, "找不到历史记录。")
        paths = {
            "video": record.video_path,
            "transcript": record.transcription_path,
            "markdown": record.markdown_path,
        }
        if query.file_kind not in paths:
            raise ApplicationError(404, "不支持这种文件类型。")
        raw_path = paths[query.file_kind]
        if not raw_path:
            label = {"video": "视频", "transcript": "转录", "markdown": "Markdown 笔记"}[query.file_kind]
            raise ApplicationError(404, f"此任务没有保存{label}文件。")
        settings = load_settings()
        if query.file_kind == "markdown":
            try:
                return resolve_markdown_file(raw_path, settings.notes_dir)
            except (FileNotFoundError, ValueError) as exc:
                raise ApplicationError(404, str(exc)) from exc
        requested = Path(raw_path).expanduser()
        candidates = [requested]
        if not requested.is_absolute():
            candidates.append(Path(__file__).resolve().parents[3] / requested)
        candidates.append(Path(settings.download_dir).expanduser() / requested.name)
        for candidate in candidates:
            if candidate.is_file():
                return candidate.resolve()
        raise ApplicationError(404, f"文件不存在：{raw_path}")


class ListFavoritesHandler:
    def handle(self, _query: ListFavoritesQuery) -> list[dict]:
        items = favorite_store().list_items()
        tags_by_task = tag_store().tags_for_tasks([item.task_id for item in items])
        return [favorite_dict(item, tags_by_task.get(item.task_id, [])) for item in items]


class ListFavoriteFoldersHandler:
    def handle(self, _query: ListFavoriteFoldersQuery) -> list[dict]:
        return [folder.__dict__ for folder in favorite_store().list_folders()]


class CreateFavoriteFolderHandler:
    def handle(self, command: CreateFavoriteFolderCommand) -> dict:
        try:
            return favorite_store().add_folder(command.name, command.notes).__dict__
        except Exception as exc:
            raise ApplicationError(400, str(exc)) from exc


class UpdateFavoriteFolderHandler:
    def handle(self, command: UpdateFavoriteFolderCommand) -> dict:
        try:
            folder = favorite_store().update_folder(command.folder_id, command.name, command.notes)
        except Exception as exc:
            raise ApplicationError(400, str(exc)) from exc
        if folder is None:
            raise ApplicationError(404, "找不到收藏文件夹。")
        return folder.__dict__


class DeleteFavoriteFolderHandler:
    def handle(self, command: DeleteFavoriteFolderCommand) -> dict:
        if not favorite_store().delete_folder(command.folder_id):
            raise ApplicationError(404, "找不到收藏文件夹。")
        return {"deleted": True}


class CreateFavoriteHandler:
    def handle(self, command: CreateFavoriteCommand) -> dict:
        record = history_store().get_record(command.task_id)
        if record is None:
            raise ApplicationError(404, "找不到历史记录。")
        if not record.summary and not record.markdown_path:
            raise ApplicationError(400, "此任务尚未生成总结或 Markdown 笔记。")
        item = favorite_store().add_from_history(record, command.folder_id)
        return favorite_dict(item, tag_store().tags_for_task(item.task_id))


class ReadFavoriteMarkdownHandler:
    def handle(self, query: ReadFavoriteMarkdownQuery) -> dict:
        item = favorite_store().get_item(query.item_id)
        if item is None:
            raise ApplicationError(404, "找不到收藏笔记。")
        if not item.markdown_path:
            raise ApplicationError(404, "此收藏没有 Markdown 文件路径。")
        try:
            document = read_markdown_file(item.markdown_path, load_settings().notes_dir)
        except (FileNotFoundError, ValueError, UnicodeDecodeError) as exc:
            raise ApplicationError(404, str(exc)) from exc
        return document.__dict__


class AssignFavoriteFolderHandler:
    def handle(self, command: AssignFavoriteFolderCommand) -> dict:
        try:
            item = favorite_store().assign_folder(command.item_id, command.folder_id)
        except ValueError as exc:
            raise ApplicationError(404, str(exc)) from exc
        return favorite_dict(item, tag_store().tags_for_task(item.task_id))


class UpdateFavoriteTagsHandler:
    def handle(self, command: UpdateFavoriteTagsCommand) -> dict:
        item = favorite_store().get_item(command.item_id)
        if item is None:
            raise ApplicationError(404, "找不到收藏笔记。")
        try:
            tags = tag_store().set_task_tags(item.task_id, command.tags)
        except ValueError as exc:
            raise ApplicationError(400, str(exc)) from exc
        return favorite_dict(item, tags)


class DeleteFavoriteHandler:
    def handle(self, command: DeleteFavoriteCommand) -> dict:
        if not favorite_store().delete_item(command.item_id):
            raise ApplicationError(404, "找不到收藏笔记。")
        return {"deleted": True}
