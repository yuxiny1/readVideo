from fastapi import APIRouter, Query

from backend.api.schemas import WatchItemRequest, WatchItemUpdateRequest, WatchlistReorderRequest
from backend.application import get_mediator
from backend.application.messages.watchlist import (
    AddWatchItemCommand,
    DeleteWatchItemCommand,
    ListWatchItemUpdatesQuery,
    ListWatchlistQuery,
    ReorderWatchlistCommand,
    UpdateWatchItemCommand,
)


router = APIRouter()


@router.get("/watchlist")
async def list_watchlist():
    return await get_mediator().send(ListWatchlistQuery())


@router.post("/watchlist")
async def add_watch_item(request: WatchItemRequest):
    return await get_mediator().send(AddWatchItemCommand(request.name, str(request.url), request.notes))


@router.patch("/watchlist/reorder")
async def reorder_watch_items(request: WatchlistReorderRequest):
    return await get_mediator().send(ReorderWatchlistCommand(request.item_ids))


@router.delete("/watchlist/{item_id}")
async def delete_watch_item(item_id: int):
    return await get_mediator().send(DeleteWatchItemCommand(item_id))


@router.patch("/watchlist/{item_id}")
async def update_watch_item(item_id: int, request: WatchItemUpdateRequest):
    command = UpdateWatchItemCommand(item_id, request.name, str(request.url), request.notes)
    return await get_mediator().send(command)


@router.get("/watchlist/{item_id}/updates")
async def list_watch_item_updates(item_id: int, limit: int = Query(default=8, ge=1, le=50)):
    return await get_mediator().send(ListWatchItemUpdatesQuery(item_id, limit))
