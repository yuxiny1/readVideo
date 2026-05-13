import asyncio
import logging
from dataclasses import replace
from pathlib import Path
from typing import Optional

from backend.core.config import Settings, load_settings
from backend.core.task_state import get_task, set_task_status
from backend.services.downloader import download_video
from backend.services.local_transcription import LocalWhisperTranscription
from backend.services.notes import write_markdown_note
from backend.services.openai_transcription import AudioTranscription
from backend.storage.history import HistoryStore


logger = logging.getLogger(__name__)


def transcribe_video(video_path: str, settings: Settings):
    if settings.transcription_backend == "local":
        service = LocalWhisperTranscription(
            whisper_cli=settings.local_whisper_cli,
            model_path=settings.local_whisper_model,
            language=settings.local_whisper_language,
            prompt=settings.local_whisper_prompt,
            audio_filter=settings.local_whisper_audio_filter,
        )
        return service.process_video(video_path)

    service = AudioTranscription(
        api_key=settings.openai_api_key,
        model=settings.transcription_model,
        language=settings.local_whisper_language,
        prompt=settings.local_whisper_prompt,
    )
    return service.process_video(video_path, settings.chunk_seconds)


async def process_video(
    task_id: str,
    url: str,
    transcription_backend: Optional[str] = None,
    transcription_model: Optional[str] = None,
    transcription_prompt: Optional[str] = None,
    local_whisper_model: Optional[str] = None,
    local_whisper_language: Optional[str] = None,
    notes_dir: Optional[str] = None,
    notes_backend: Optional[str] = None,
    ollama_model: Optional[str] = None,
):
    settings = None
    try:
        settings = load_settings()
        settings = resolve_transcription_settings(
            settings,
            transcription_backend,
            transcription_model,
            transcription_prompt,
            local_whisper_model,
            local_whisper_language,
        )
        resolved_notes_backend = resolve_notes_backend(notes_backend, settings.notes_backend)
        resolved_ollama_model = ollama_model or settings.ollama_model
        set_task_status(task_id, "downloading", url=url)
        persist_task_history(settings.database_path, task_id)

        downloaded_file_path = await asyncio.to_thread(download_video, url, settings.download_dir)
        video_title = Path(downloaded_file_path).stem
        set_task_status(task_id, "transcribing", url=url, title=video_title, video_path=downloaded_file_path)
        persist_task_history(settings.database_path, task_id)

        result = await asyncio.to_thread(transcribe_video, downloaded_file_path, settings)
        set_task_status(
            task_id,
            "organizing_notes",
            url=url,
            title=video_title,
            video_path=downloaded_file_path,
            transcription_path=result.transcription_path,
        )
        persist_task_history(settings.database_path, task_id)

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
            title=video_title,
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
        persist_task_history(settings.database_path, task_id)
    except Exception as exc:
        logger.exception("Task %s failed", task_id)
        set_task_status(task_id, "failed", url=url, error=str(exc))
        if settings is not None:
            persist_task_history(settings.database_path, task_id)


def resolve_notes_backend(request_backend: Optional[str], default_backend: str) -> str:
    backend = (request_backend or default_backend).lower()
    if backend not in {"extractive", "ollama"}:
        raise RuntimeError("notes_backend must be extractive or ollama.")
    return backend


def resolve_transcription_settings(
    settings: Settings,
    transcription_backend: Optional[str] = None,
    transcription_model: Optional[str] = None,
    transcription_prompt: Optional[str] = None,
    local_whisper_model: Optional[str] = None,
    local_whisper_language: Optional[str] = None,
) -> Settings:
    backend = (transcription_backend or settings.transcription_backend).lower()
    if backend not in {"local", "openai"}:
        raise ValueError("transcription_backend must be local or openai")
    if backend == "openai" and not settings.openai_api_key:
        raise ValueError("Set OPENAI_API_KEY before using the OpenAI transcription backend")

    return replace(
        settings,
        transcription_backend=backend,
        transcription_model=transcription_model or settings.transcription_model,
        local_whisper_model=local_whisper_model or settings.local_whisper_model,
        local_whisper_language=local_whisper_language or settings.local_whisper_language,
        local_whisper_prompt=(transcription_prompt or settings.local_whisper_prompt or "").strip(),
    )


def persist_task_history(database_path: str, task_id: str):
    task = get_task(task_id)
    if task is not None:
        HistoryStore(database_path).upsert_task(task)
