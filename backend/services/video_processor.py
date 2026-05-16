import asyncio
import logging
from dataclasses import dataclass, replace
import time
from pathlib import Path
from typing import Optional

from backend.core.config import Settings, load_openai_api_key, load_settings
from backend.core.task_state import append_task_log, get_task, set_task_status, update_task_details
from backend.services.downloader import download_video
from backend.services.history_reuse import find_history_reuse_candidate, resolve_existing_path
from backend.services.local_transcription import LocalWhisperTranscription
from backend.services.notes import write_markdown_note
from backend.services.openai_transcription import AudioTranscription
from backend.storage.history import HistoryStore


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExistingTranscriptionResult:
    text: str
    transcription_path: str
    chunk_count: Optional[int] = None


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
    notes_dir: Optional[str] = None,
    notes_backend: Optional[str] = None,
    ollama_model: Optional[str] = None,
    reuse_task_id: Optional[str] = None,
    force_download: bool = False,
    delete_video_after_completion: bool = False,
    transcription_backend: Optional[str] = None,
    transcription_model: Optional[str] = None,
    transcription_prompt: Optional[str] = None,
    local_whisper_model: Optional[str] = None,
    local_whisper_language: Optional[str] = None,
):
    settings = None
    try:
        settings = resolve_transcription_settings(
            load_settings(),
            transcription_backend=transcription_backend,
            transcription_model=transcription_model,
            transcription_prompt=transcription_prompt,
            local_whisper_model=local_whisper_model,
            local_whisper_language=local_whisper_language,
        )
        resolved_notes_backend = resolve_notes_backend(notes_backend, settings.notes_backend)
        resolved_ollama_model = ollama_model or settings.ollama_model
        candidate = None
        if not force_download:
            candidate = find_history_reuse_candidate(
                settings.database_path,
                url,
                settings.download_dir,
                task_id=reuse_task_id,
            )

        if candidate is not None and candidate.video_path is not None:
            downloaded_file_path = str(candidate.video_path)
            video_title = candidate.record.title or candidate.video_path.stem
            set_task_status(
                task_id,
                "transcribing",
                url=url,
                title=video_title,
                video_path=downloaded_file_path,
                notes_backend=resolved_notes_backend,
                ollama_model=resolved_ollama_model if resolved_notes_backend == "ollama" else None,
                transcription_backend=settings.transcription_backend,
                transcription_model=settings.transcription_model if settings.transcription_backend == "openai" else None,
                local_whisper_model=settings.local_whisper_model if settings.transcription_backend == "local" else None,
                local_whisper_language=settings.local_whisper_language if settings.transcription_backend == "local" else None,
                delete_video_after_completion=delete_video_after_completion,
                download_status="reused",
                download_percent=100,
                reused_from_task_id=candidate.record.task_id,
                log_message=f"Using existing downloaded video from task {candidate.record.task_id}: {downloaded_file_path}",
            )
            persist_task_history(settings.database_path, task_id)
        else:
            reuse_note = ""
            if candidate is not None:
                reuse_note = " History had this URL, but the saved video file is missing; downloading again."
            set_task_status(
                task_id,
                "downloading",
                url=url,
                notes_backend=resolved_notes_backend,
                ollama_model=resolved_ollama_model if resolved_notes_backend == "ollama" else None,
                transcription_backend=settings.transcription_backend,
                transcription_model=settings.transcription_model if settings.transcription_backend == "openai" else None,
                local_whisper_model=settings.local_whisper_model if settings.transcription_backend == "local" else None,
                local_whisper_language=settings.local_whisper_language if settings.transcription_backend == "local" else None,
                delete_video_after_completion=delete_video_after_completion,
                download_dir=settings.download_dir,
                force_download=force_download,
                log_message=f"Downloading from {url}.{reuse_note}",
            )
            persist_task_history(settings.database_path, task_id)

            downloaded_file_path = await asyncio.to_thread(
                download_video,
                url,
                settings.download_dir,
                build_download_progress_hook(task_id),
            )
            video_title = Path(downloaded_file_path).stem
            set_task_status(
                task_id,
                "transcribing",
                url=url,
                title=video_title,
                video_path=downloaded_file_path,
                delete_video_after_completion=delete_video_after_completion,
                download_percent=100,
                download_status="finished",
                log_message=f"Download saved to {downloaded_file_path}",
            )
            persist_task_history(settings.database_path, task_id)

        if candidate is not None and candidate.video_path is not None and candidate.transcript_path is not None:
            transcript_text = candidate.transcript_path.read_text(encoding="utf-8")
            result = ExistingTranscriptionResult(text=transcript_text, transcription_path=str(candidate.transcript_path))
            resolved_transcription_backend = "reused"
            set_task_status(
                task_id,
                "organizing_notes",
                url=url,
                title=video_title,
                video_path=downloaded_file_path,
                transcription_path=result.transcription_path,
                transcription_backend="reused",
                log_message=f"Using existing transcript: {result.transcription_path}",
            )
            persist_task_history(settings.database_path, task_id)
        else:
            append_task_log(task_id, f"Transcribing with {settings.transcription_backend}.", status="transcribing")
            result = await asyncio.to_thread(transcribe_video, downloaded_file_path, settings)
            resolved_transcription_backend = settings.transcription_backend
            set_task_status(
                task_id,
                "organizing_notes",
                url=url,
                title=video_title,
                video_path=downloaded_file_path,
                transcription_path=result.transcription_path,
                transcription_backend=settings.transcription_backend,
                chunk_count=getattr(result, "chunk_count", None),
                log_message=f"Transcript saved to {result.transcription_path}",
            )
            persist_task_history(settings.database_path, task_id)

        if resolved_notes_backend == "ollama":
            append_task_log(
                task_id,
                f"Writing article-style AI notes with Ollama model {resolved_ollama_model}.",
                status="organizing_notes",
            )
        else:
            append_task_log(task_id, "Writing quick notes without an AI model.", status="organizing_notes")
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
            transcription_backend=resolved_transcription_backend,
            summary_backend=note_result.summary_backend,
            ollama_model=resolved_ollama_model if resolved_notes_backend == "ollama" else None,
            chunk_count=getattr(result, "chunk_count", None),
            delete_video_after_completion=delete_video_after_completion,
            log_message=f"Markdown note saved to {note_result.markdown_path}",
        )
        persist_task_history(settings.database_path, task_id)
        if delete_video_after_completion:
            delete_downloaded_video_after_completion(task_id, downloaded_file_path, settings.download_dir)
            persist_task_history(settings.database_path, task_id)
    except Exception as exc:
        logger.exception("Task %s failed", task_id)
        set_task_status(task_id, "failed", url=url, error=str(exc), log_message=str(exc), log_level="error")
        if settings is not None:
            persist_task_history(settings.database_path, task_id)


def delete_downloaded_video_after_completion(task_id: str, video_path: str, download_dir: str) -> bool:
    path = resolve_existing_path(video_path, download_dir)
    if path is None:
        message = "Delete requested, but the local video file was already missing."
        update_task_details(
            task_id,
            video_deleted_after_completion=False,
            video_delete_error=message,
        )
        append_task_log(task_id, message, status="completed")
        return False

    try:
        path.unlink()
    except OSError as exc:
        message = f"Could not delete local video {path}: {exc}"
        update_task_details(
            task_id,
            video_deleted_after_completion=False,
            video_delete_error=str(exc),
        )
        append_task_log(task_id, message, level="error", status="completed")
        return False

    update_task_details(
        task_id,
        video_deleted_after_completion=True,
        video_delete_error="",
        download_status="deleted_after_completion",
        download_filename=path.name,
    )
    append_task_log(task_id, f"Deleted local video after completion: {path}", status="completed")
    return True


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
        raise RuntimeError("transcription_backend must be local or openai.")

    openai_api_key = settings.openai_api_key
    if backend == "openai" and not openai_api_key:
        openai_api_key = load_openai_api_key(required=True)

    return replace(
        settings,
        transcription_backend=backend,
        openai_api_key=openai_api_key,
        transcription_model=transcription_model or settings.transcription_model,
        local_whisper_model=local_whisper_model or settings.local_whisper_model,
        local_whisper_language=local_whisper_language or settings.local_whisper_language,
        local_whisper_prompt=(transcription_prompt or settings.local_whisper_prompt or "").strip(),
    )


def persist_task_history(database_path: str, task_id: str):
    task = get_task(task_id)
    if task is not None:
        HistoryStore(database_path).upsert_task(task)


def build_download_progress_hook(task_id: str):
    last_update = 0.0
    last_bucket = -10

    def report(progress: dict):
        nonlocal last_update, last_bucket
        status = progress.get("status")
        filename = progress.get("filename") or progress.get("tmpfilename") or ""
        total_bytes = progress.get("total_bytes") or progress.get("total_bytes_estimate")
        downloaded_bytes = progress.get("downloaded_bytes")
        percent = _download_percent(downloaded_bytes, total_bytes)
        now = time.monotonic()

        if status == "downloading" and now - last_update >= 0.8:
            last_update = now
            update_task_details(
                task_id,
                download_status="downloading",
                download_filename=Path(filename).name if filename else "",
                download_percent=percent,
                downloaded_bytes=downloaded_bytes,
                download_total_bytes=total_bytes,
                download_speed=progress.get("speed"),
                download_eta=progress.get("eta"),
            )

        if status == "downloading" and percent is not None:
            bucket = int(percent // 10) * 10
            if bucket > last_bucket:
                last_bucket = bucket
                append_task_log(task_id, f"Download {percent:.1f}% complete.", status="downloading")

        if status == "finished":
            update_task_details(
                task_id,
                download_status="finished",
                download_filename=Path(filename).name if filename else "",
                download_percent=100,
                downloaded_bytes=downloaded_bytes,
                download_total_bytes=total_bytes,
                download_speed=progress.get("speed"),
                download_eta=0,
            )
            append_task_log(task_id, "Download finished; preparing transcription.", status="downloading")

    return report


def _download_percent(downloaded_bytes: Optional[float], total_bytes: Optional[float]) -> Optional[float]:
    if not downloaded_bytes or not total_bytes:
        return None
    return min(100.0, round((downloaded_bytes / total_bytes) * 100, 1))
