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
from backend.services.local_transcription import LocalWhisperTranscription, read_transcript_text
from backend.services.notes import write_markdown_note
from backend.services.openai_transcription import AudioTranscription
from backend.storage.history import HistoryStore


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExistingTranscriptionResult:
    text: str
    transcription_path: str
    chunk_count: Optional[int] = None
    recovered_encoding: bool = False
    decode_error: str = ""


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
    note_style: Optional[str] = None,
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
        resolved_note_style = resolve_note_style(note_style, settings.note_style)
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
                note_style=resolved_note_style,
                ollama_model=resolved_ollama_model if resolved_notes_backend == "ollama" else None,
                transcription_backend=settings.transcription_backend,
                transcription_model=settings.transcription_model if settings.transcription_backend == "openai" else None,
                local_whisper_model=settings.local_whisper_model if settings.transcription_backend == "local" else None,
                local_whisper_language=settings.local_whisper_language if settings.transcription_backend == "local" else None,
                delete_video_after_completion=delete_video_after_completion,
                download_status="reused",
                download_percent=100,
                reused_from_task_id=candidate.record.task_id,
                log_message=f"正在复用任务 {candidate.record.task_id} 已下载的视频：{downloaded_file_path}",
            )
            persist_task_history(settings.database_path, task_id)
        else:
            reuse_note = ""
            if candidate is not None:
                reuse_note = "历史记录中已有此网址，但本地视频不存在，将重新下载。"
            set_task_status(
                task_id,
                "downloading",
                url=url,
                notes_backend=resolved_notes_backend,
                note_style=resolved_note_style,
                ollama_model=resolved_ollama_model if resolved_notes_backend == "ollama" else None,
                transcription_backend=settings.transcription_backend,
                transcription_model=settings.transcription_model if settings.transcription_backend == "openai" else None,
                local_whisper_model=settings.local_whisper_model if settings.transcription_backend == "local" else None,
                local_whisper_language=settings.local_whisper_language if settings.transcription_backend == "local" else None,
                delete_video_after_completion=delete_video_after_completion,
                download_dir=settings.download_dir,
                force_download=force_download,
                log_message=f"正在从 {url} 下载视频。{reuse_note}",
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
                log_message=f"视频已保存至：{downloaded_file_path}",
            )
            persist_task_history(settings.database_path, task_id)

        if candidate is not None and candidate.video_path is not None and candidate.transcript_path is not None:
            transcript = read_transcript_text(candidate.transcript_path)
            if transcript.recovered_encoding:
                candidate.transcript_path.write_text(transcript.text, encoding="utf-8")
            result = ExistingTranscriptionResult(
                text=transcript.text,
                transcription_path=str(candidate.transcript_path),
                recovered_encoding=transcript.recovered_encoding,
                decode_error=transcript.decode_error,
            )
            resolved_transcription_backend = "reused"
            set_task_status(
                task_id,
                "organizing_notes",
                url=url,
                title=video_title,
                video_path=downloaded_file_path,
                transcription_path=result.transcription_path,
                transcription_backend="reused",
                log_message=f"正在复用已有转录文件：{result.transcription_path}",
            )
            append_transcript_recovery_log(task_id, result)
            persist_task_history(settings.database_path, task_id)
        else:
            transcription_label = "本地 Whisper" if settings.transcription_backend == "local" else "OpenAI 转录"
            append_task_log(task_id, f"正在使用{transcription_label}。", status="transcribing")
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
                log_message=f"转录文件已保存至：{result.transcription_path}",
            )
            append_transcript_recovery_log(task_id, result)
            persist_task_history(settings.database_path, task_id)

        if resolved_notes_backend == "ollama":
            style_label = "商业分析文章" if resolved_note_style == "commercial" else "高细节段落笔记"
            append_task_log(
                task_id,
                f"正在使用 Ollama 模型 {resolved_ollama_model} 生成{style_label}。",
                status="organizing_notes",
            )
        else:
            append_task_log(task_id, "正在整理本地提取式笔记。", status="organizing_notes")
        note_result = await asyncio.to_thread(
            write_markdown_note,
            transcript_text=result.text,
            video_title=video_title,
            source_url=url,
            output_dir=notes_dir or settings.notes_dir,
            transcript_path=result.transcription_path,
            summary_backend=resolved_notes_backend,
            ollama_model=resolved_ollama_model,
            ollama_url=settings.ollama_url,
            note_style=resolved_note_style,
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
            note_style=resolved_note_style,
            chunk_count=getattr(result, "chunk_count", None),
            delete_video_after_completion=delete_video_after_completion,
            log_message=f"Markdown 笔记已保存至：{note_result.markdown_path}",
        )
        persist_task_history(settings.database_path, task_id)
        if delete_video_after_completion:
            delete_downloaded_video_after_completion(task_id, downloaded_file_path, settings.download_dir)
            persist_task_history(settings.database_path, task_id)
    except Exception as exc:
        logger.exception("任务 %s 失败", task_id)
        set_task_status(task_id, "failed", url=url, error=str(exc), log_message=str(exc), log_level="error")
        if settings is not None:
            persist_task_history(settings.database_path, task_id)


def delete_downloaded_video_after_completion(task_id: str, video_path: str, download_dir: str) -> bool:
    path = resolve_existing_path(video_path, download_dir)
    if path is None:
        message = "已请求删除视频，但本地视频文件不存在。"
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
        message = f"无法删除本地视频 {path}：{exc}"
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
    append_task_log(task_id, f"任务完成后已删除本地视频：{path}", status="completed")
    return True


def append_transcript_recovery_log(task_id: str, result):
    if not getattr(result, "recovered_encoding", False):
        return
    append_task_log(
        task_id,
        (
            "转录文件包含无效的 UTF-8 字节；已恢复可读内容、重新写入 UTF-8，"
            f"并继续处理：{result.transcription_path}"
        ),
        level="warning",
        status="organizing_notes",
    )


def resolve_notes_backend(request_backend: Optional[str], default_backend: str) -> str:
    backend = (request_backend or default_backend).lower()
    if backend not in {"extractive", "ollama"}:
        raise RuntimeError("笔记引擎无效，请选择本地提取式笔记或 Ollama 本地大模型。")
    return backend


def resolve_note_style(request_style: Optional[str], default_style: str) -> str:
    style = (request_style or default_style).lower()
    if style not in {"detailed", "commercial"}:
        raise RuntimeError("笔记风格无效，请选择详细笔记或商业分析。")
    return style


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
        raise RuntimeError("转录引擎无效，请选择本地 Whisper 或 OpenAI 转录。")

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
                append_task_log(task_id, f"下载进度：{percent:.1f}%。", status="downloading")

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
            append_task_log(task_id, "下载完成，正在准备转录。", status="downloading")

    return report


def _download_percent(downloaded_bytes: Optional[float], total_bytes: Optional[float]) -> Optional[float]:
    if not downloaded_bytes or not total_bytes:
        return None
    return min(100.0, round((downloaded_bytes / total_bytes) * 100, 1))
