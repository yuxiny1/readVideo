from backend.application.errors import ApplicationError
from backend.application.handlers.dependencies import watchlist_store
from backend.application.messages.watchlist import (
    AddWatchItemCommand,
    DeleteWatchItemCommand,
    ListWatchItemUpdatesQuery,
    ListWatchlistQuery,
    ReorderWatchlistCommand,
    UpdateWatchItemCommand,
)
from backend.services.source_updates import list_source_updates


class ListWatchlistHandler:
    def handle(self, _query: ListWatchlistQuery) -> list[dict]:
        return [item.__dict__ for item in watchlist_store().list_items()]


class AddWatchItemHandler:
    def handle(self, command: AddWatchItemCommand) -> dict:
        return watchlist_store().add_item(command.name, command.url, command.notes).__dict__


class ReorderWatchlistHandler:
    def handle(self, command: ReorderWatchlistCommand) -> list[dict]:
        try:
            items = watchlist_store().reorder_items(command.item_ids)
        except ValueError as exc:
            raise ApplicationError(404, str(exc)) from exc
        return [item.__dict__ for item in items]


class DeleteWatchItemHandler:
    def handle(self, command: DeleteWatchItemCommand) -> dict:
        if not watchlist_store().delete_item(command.item_id):
            raise ApplicationError(404, "找不到订阅源。")
        return {"deleted": True}


class UpdateWatchItemHandler:
    def handle(self, command: UpdateWatchItemCommand) -> dict:
        item = watchlist_store().update_item(command.item_id, command.name, command.url, command.notes)
        if item is None:
            raise ApplicationError(404, "找不到订阅源。")
        return item.__dict__


class ListWatchItemUpdatesHandler:
    def handle(self, query: ListWatchItemUpdatesQuery) -> dict:
        item = watchlist_store().get_item(query.item_id)
        if item is None:
            raise ApplicationError(404, "找不到订阅源。")
        try:
            updates = list_source_updates(item.url, query.limit)
        except Exception as exc:
            raise ApplicationError(400, f"无法获取订阅源更新：{exc}") from exc
        return {"source": item.__dict__, "updates": [update.__dict__ for update in updates]}
