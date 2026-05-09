import asyncio
import logging
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, HttpUrl

from audioTranscription import AudioTranscription
from config import Settings, load_settings
from local_transcription import LocalWhisperTranscription
from notes import write_markdown_note
from watchlist import WatchlistStore
from yt_dl import download_video


logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
app = FastAPI(title="readVideo")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
TASKS = {}


class ProcessVideoRequest(BaseModel):
    url: HttpUrl
    task_id: Optional[str] = Field(default=None, min_length=1)
    notes_dir: Optional[str] = Field(default=None, min_length=1)
    notes_backend: Optional[str] = Field(default=None, min_length=1)
    ollama_model: Optional[str] = Field(default=None, min_length=1)


class WatchItemRequest(BaseModel):
    name: str = Field(min_length=1)
    url: HttpUrl
    notes: str = ""


def set_task_status(task_id: str, status: str, **details):
    TASKS[task_id] = {"task_id": task_id, "status": status, **details}


def get_store() -> WatchlistStore:
    return WatchlistStore(load_settings().database_path)


def transcribe_video(video_path: str, settings: Settings):
    if settings.transcription_backend == "local":
        service = LocalWhisperTranscription(
            whisper_cli=settings.local_whisper_cli,
            model_path=settings.local_whisper_model,
            language=settings.local_whisper_language,
        )
        return service.process_video(video_path)

    service = AudioTranscription(
        api_key=settings.openai_api_key,
        model=settings.transcription_model,
    )
    return service.process_video(video_path, settings.chunk_seconds)


async def process_video(
    task_id: str,
    url: str,
    notes_dir: Optional[str] = None,
    notes_backend: Optional[str] = None,
    ollama_model: Optional[str] = None,
):
    try:
        settings = load_settings()
        resolved_notes_backend = _resolve_notes_backend(notes_backend, settings.notes_backend)
        resolved_ollama_model = ollama_model or settings.ollama_model
        set_task_status(task_id, "downloading", url=url)

        downloaded_file_path = await asyncio.to_thread(download_video, url, settings.download_dir)
        set_task_status(task_id, "transcribing", url=url, video_path=downloaded_file_path)

        result = await asyncio.to_thread(transcribe_video, downloaded_file_path, settings)
        set_task_status(
            task_id,
            "organizing_notes",
            url=url,
            video_path=downloaded_file_path,
            transcription_path=result.transcription_path,
        )

        video_title = _title_from_path(downloaded_file_path)
        note_result = await asyncio.to_thread(
            write_markdown_note,
            result.text,
            video_title,
            url,
            notes_dir or settings.notes_dir,
            result.transcription_path,
            resolved_notes_backend,
            resolved_ollama_model,
            settings.ollama_url,
        )

        set_task_status(
            task_id,
            "completed",
            url=url,
            video_path=downloaded_file_path,
            transcription_path=result.transcription_path,
            markdown_path=note_result.markdown_path,
            summary=note_result.summary,
            section_count=note_result.section_count,
            transcription_backend=settings.transcription_backend,
            summary_backend=note_result.summary_backend,
            ollama_model=resolved_ollama_model if resolved_notes_backend == "ollama" else None,
            chunk_count=getattr(result, "chunk_count", None),
        )
    except Exception as exc:
        logger.exception("Task %s failed", task_id)
        set_task_status(task_id, "failed", url=url, error=str(exc))


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/process_video/")
async def create_task(request: ProcessVideoRequest, background_tasks: BackgroundTasks):
    try:
        settings = load_settings()
        _resolve_notes_backend(request.notes_backend, settings.notes_backend)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    task_id = request.task_id or str(uuid4())
    set_task_status(task_id, "queued", url=str(request.url))
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


@app.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    task = TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/watchlist")
async def list_watchlist():
    return [item.__dict__ for item in get_store().list_items()]


@app.post("/watchlist")
async def add_watch_item(request: WatchItemRequest):
    item = get_store().add_item(request.name, str(request.url), request.notes)
    return item.__dict__


@app.delete("/watchlist/{item_id}")
async def delete_watch_item(item_id: int):
    deleted = get_store().delete_item(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Watch item not found")
    return {"deleted": True}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/app_config")
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


def _title_from_path(path: str) -> str:
    from pathlib import Path

    return Path(path).stem


def _resolve_notes_backend(request_backend: Optional[str], default_backend: str) -> str:
    backend = (request_backend or default_backend).lower()
    if backend not in {"extractive", "ollama"}:
        raise RuntimeError("notes_backend must be extractive or ollama.")
    return backend


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
