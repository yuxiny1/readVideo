from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from fastapi.responses import FileResponse

from backend.api.schemas import (
    FavoriteFolderAssignmentRequest,
    FavoriteFolderRequest,
    FavoriteRequest,
    OllamaPullRequest,
    ProcessVideoRequest,
    WatchItemRequest,
    WatchItemUpdateRequest,
    WatchlistReorderRequest,
)
from backend.core.config import load_settings
from backend.core.task_state import get_task, list_tasks, set_task_status
from backend.services.markdown_files import list_markdown_files, read_markdown_file, resolve_markdown_file
from backend.services.ollama_models import list_installed_models, pull_model, recommended_models
from backend.services.source_updates import list_source_updates
from backend.services.video_processor import process_video, resolve_notes_backend
from backend.storage.favorites import FavoriteStore
from backend.storage.history import HistoryStore
from backend.storage.watchlist import WatchlistStore


router = APIRouter()
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_store() -> WatchlistStore:
    return WatchlistStore(load_settings().database_path)


def get_history_store() -> HistoryStore:
    return HistoryStore(load_settings().database_path)


def get_favorite_store() -> FavoriteStore:
    return FavoriteStore(load_settings().database_path)


def resolve_history_file(path: str) -> Path:
    file_path = Path(path).expanduser()
    if not file_path.is_absolute():
        file_path = PROJECT_ROOT / file_path
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"File does not exist: {path}")
    return file_path


@router.post("/process_video/")
async def create_task(request: ProcessVideoRequest, background_tasks: BackgroundTasks):
    try:
        settings = load_settings()
        resolve_notes_backend(request.notes_backend, settings.notes_backend)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    task_id = request.task_id or str(uuid4())
    set_task_status(task_id, "queued", url=str(request.url))
    queued_task = get_task(task_id)
    if queued_task is not None:
        HistoryStore(settings.database_path).upsert_task(queued_task)
    background_tasks.add_task(
        process_video,
        task_id,
        str(request.url),
        request.notes_dir,
        request.notes_backend,
        request.ollama_model,
    )

    return {
        "task_id": task_id,
        "status": "queued",
        "status_url": f"/task_status/{task_id}",
    }


@router.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/tasks")
async def get_tasks():
    return list_tasks()


@router.get("/api/history")
async def list_history():
    return [record.__dict__ for record in get_history_store().list_records()]


@router.get("/api/history/{task_id}")
async def get_history(task_id: str):
    record = get_history_store().get_record(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="History record not found")
    return record.__dict__


@router.get("/api/history/{task_id}/files/{file_kind}")
async def download_history_file(task_id: str, file_kind: str):
    record = get_history_store().get_record(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="History record not found")

    paths = {
        "video": record.video_path,
        "transcript": record.transcription_path,
        "markdown": record.markdown_path,
    }
    if file_kind not in paths:
        raise HTTPException(status_code=404, detail="Unknown file kind")

    file_path = paths[file_kind]
    if not file_path:
        raise HTTPException(status_code=404, detail=f"No {file_kind} file saved for this task")

    try:
        path = resolve_history_file(file_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return FileResponse(path, filename=path.name)


@router.get("/api/favorites")
async def list_favorites():
    return [item.__dict__ for item in get_favorite_store().list_items()]


@router.get("/api/favorites/folders")
async def list_favorite_folders():
    return [folder.__dict__ for folder in get_favorite_store().list_folders()]


@router.post("/api/favorites/folders")
async def add_favorite_folder(request: FavoriteFolderRequest):
    try:
        folder = get_favorite_store().add_folder(request.name, request.notes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return folder.__dict__


@router.delete("/api/favorites/folders/{folder_id}")
async def delete_favorite_folder(folder_id: int):
    deleted = get_favorite_store().delete_folder(folder_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Favorite folder not found")
    return {"deleted": True}


@router.post("/api/favorites")
async def add_favorite(request: FavoriteRequest):
    record = get_history_store().get_record(request.task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="History record not found")
    if not record.summary and not record.markdown_path:
        raise HTTPException(status_code=400, detail="This task has no summary or Markdown note yet.")

    try:
        item = get_favorite_store().add_from_history(record, request.folder_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return item.__dict__


@router.get("/api/favorites/{item_id}/markdown")
async def read_favorite_markdown(item_id: int):
    item = get_favorite_store().get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Favorite not found")
    if not item.markdown_path:
        raise HTTPException(status_code=404, detail="This favorite has no Markdown path")
    try:
        document = read_markdown_file(item.markdown_path)
    except (FileNotFoundError, ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return document.__dict__


@router.patch("/api/favorites/{item_id}/folder")
async def assign_favorite_folder(item_id: int, request: FavoriteFolderAssignmentRequest):
    try:
        item = get_favorite_store().assign_folder(item_id, request.folder_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return item.__dict__


@router.delete("/api/favorites/{item_id}")
async def delete_favorite(item_id: int):
    deleted = get_favorite_store().delete_item(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"deleted": True}


@router.get("/api/markdown_files")
async def get_markdown_files(directory: str = Query(default="")):
    settings = load_settings()
    folder = directory or settings.notes_dir
    try:
        files = list_markdown_files(folder)
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [item.__dict__ for item in files]


@router.get("/api/markdown_files/download")
async def download_markdown_file(path: str):
    try:
        markdown_path = resolve_markdown_file(path)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        markdown_path,
        filename=markdown_path.name,
        media_type="text/markdown",
    )


@router.get("/api/markdown_files/read")
async def read_markdown_file_endpoint(path: str):
    try:
        document = read_markdown_file(path)
    except (FileNotFoundError, ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return document.__dict__


@router.get("/watchlist")
async def list_watchlist():
    return [item.__dict__ for item in get_store().list_items()]


@router.post("/watchlist")
async def add_watch_item(request: WatchItemRequest):
    item = get_store().add_item(request.name, str(request.url), request.notes)
    return item.__dict__


@router.patch("/watchlist/reorder")
async def reorder_watch_items(request: WatchlistReorderRequest):
    try:
        items = get_store().reorder_items(request.item_ids)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [item.__dict__ for item in items]


@router.delete("/watchlist/{item_id}")
async def delete_watch_item(item_id: int):
    deleted = get_store().delete_item(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Watch item not found")
    return {"deleted": True}


@router.patch("/watchlist/{item_id}")
async def update_watch_item(item_id: int, request: WatchItemUpdateRequest):
    item = get_store().update_item(item_id, request.name, str(request.url), request.notes)
    if item is None:
        raise HTTPException(status_code=404, detail="Watch item not found")
    return item.__dict__


@router.get("/watchlist/{item_id}/updates")
async def list_watch_item_updates(item_id: int, limit: int = Query(default=8, ge=1, le=50)):
    item = get_store().get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Watch item not found")
    try:
        updates = list_source_updates(item.url, limit)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not load source updates: {exc}") from exc
    return {
        "source": item.__dict__,
        "updates": [update.__dict__ for update in updates],
    }


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/api/ollama/models")
def get_ollama_models():
    return {
        "recommended": recommended_models(),
        "installed": list_installed_models(),
    }


@router.post("/api/ollama/pull")
def pull_ollama_model(request: OllamaPullRequest):
    try:
        output = pull_model(request.model)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"model": request.model, "output": output}


@router.get("/app_config")
async def app_config():
    settings = load_settings()
    return {
        "transcription_backend": settings.transcription_backend,
        "download_dir": settings.download_dir,
        "notes_dir": settings.notes_dir,
        "notes_backend": settings.notes_backend,
        "ollama_model": settings.ollama_model,
        "ollama_model_options": recommended_models(),
        "local_whisper_model": settings.local_whisper_model,
    }
