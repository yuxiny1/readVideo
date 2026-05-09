from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException

from backend.api.schemas import ProcessVideoRequest, WatchItemRequest
from backend.core.config import load_settings
from backend.core.task_state import get_task, list_tasks, set_task_status
from backend.services.video_processor import process_video, resolve_notes_backend
from backend.storage.history import HistoryStore
from backend.storage.watchlist import WatchlistStore


router = APIRouter()


def get_store() -> WatchlistStore:
    return WatchlistStore(load_settings().database_path)


def get_history_store() -> HistoryStore:
    return HistoryStore(load_settings().database_path)


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


@router.get("/watchlist")
async def list_watchlist():
    return [item.__dict__ for item in get_store().list_items()]


@router.post("/watchlist")
async def add_watch_item(request: WatchItemRequest):
    item = get_store().add_item(request.name, str(request.url), request.notes)
    return item.__dict__


@router.delete("/watchlist/{item_id}")
async def delete_watch_item(item_id: int):
    deleted = get_store().delete_item(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Watch item not found")
    return {"deleted": True}


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/app_config")
async def app_config():
    settings = load_settings()
    return {
        "transcription_backend": settings.transcription_backend,
        "download_dir": settings.download_dir,
        "notes_dir": settings.notes_dir,
        "notes_backend": settings.notes_backend,
        "ollama_model": settings.ollama_model,
        "local_whisper_model": settings.local_whisper_model,
    }
