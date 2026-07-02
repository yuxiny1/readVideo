from fastapi import APIRouter
from fastapi.responses import FileResponse

from backend.api.schemas import (
    FavoriteFolderAssignmentRequest,
    FavoriteFolderRequest,
    FavoriteFolderUpdateRequest,
    FavoriteRequest,
    TagAssignmentRequest,
)
from backend.application import get_mediator
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


router = APIRouter()


@router.get("/api/history")
async def list_history():
    return await get_mediator().send(ListHistoryQuery())


@router.get("/api/history/lookup")
async def lookup_history(url: str):
    return await get_mediator().send(LookupHistoryQuery(url))


@router.get("/api/history/{task_id}")
async def get_history(task_id: str):
    return await get_mediator().send(GetHistoryQuery(task_id))


@router.patch("/api/history/{task_id}/tags")
async def update_history_tags(task_id: str, request: TagAssignmentRequest):
    return await get_mediator().send(UpdateHistoryTagsCommand(task_id, request.tags))


@router.get("/api/history/{task_id}/files/{file_kind}")
async def download_history_file(task_id: str, file_kind: str):
    path = await get_mediator().send(GetHistoryFileQuery(task_id, file_kind))
    return FileResponse(path, filename=path.name)


@router.get("/api/favorites")
async def list_favorites():
    return await get_mediator().send(ListFavoritesQuery())


@router.get("/api/favorites/folders")
async def list_favorite_folders():
    return await get_mediator().send(ListFavoriteFoldersQuery())


@router.post("/api/favorites/folders")
async def add_favorite_folder(request: FavoriteFolderRequest):
    return await get_mediator().send(CreateFavoriteFolderCommand(request.name, request.notes))


@router.patch("/api/favorites/folders/{folder_id}")
async def update_favorite_folder(folder_id: int, request: FavoriteFolderUpdateRequest):
    return await get_mediator().send(UpdateFavoriteFolderCommand(folder_id, request.name, request.notes))


@router.delete("/api/favorites/folders/{folder_id}")
async def delete_favorite_folder(folder_id: int):
    return await get_mediator().send(DeleteFavoriteFolderCommand(folder_id))


@router.post("/api/favorites")
async def add_favorite(request: FavoriteRequest):
    return await get_mediator().send(CreateFavoriteCommand(request.task_id, request.folder_id))


@router.get("/api/favorites/{item_id}/markdown")
async def read_favorite_markdown(item_id: int):
    return await get_mediator().send(ReadFavoriteMarkdownQuery(item_id))


@router.patch("/api/favorites/{item_id}/folder")
async def assign_favorite_folder(item_id: int, request: FavoriteFolderAssignmentRequest):
    return await get_mediator().send(AssignFavoriteFolderCommand(item_id, request.folder_id))


@router.patch("/api/favorites/{item_id}/tags")
async def update_favorite_tags(item_id: int, request: TagAssignmentRequest):
    return await get_mediator().send(UpdateFavoriteTagsCommand(item_id, request.tags))


@router.delete("/api/favorites/{item_id}")
async def delete_favorite(item_id: int):
    return await get_mediator().send(DeleteFavoriteCommand(item_id))
