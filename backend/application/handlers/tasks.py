from uuid import uuid4

from backend.application.errors import ApplicationError
from backend.application.messages.tasks import (
    GetTaskQuery,
    ListTasksQuery,
    RunVideoProcessingCommand,
    StartVideoProcessingCommand,
    WorkerProbeCommand,
)
from backend.core.config import load_settings
from backend.core.task_state import get_task, list_tasks, set_task_status
from backend.services.task_queue import enqueue_video_processing
from backend.services.video_processor import (
    process_video,
    resolve_note_style,
    resolve_notes_backend,
    resolve_transcription_settings,
)
from backend.storage.history import HistoryStore


class StartVideoProcessingHandler:
    def handle(self, command: StartVideoProcessingCommand) -> dict:
        try:
            settings = load_settings()
            resolve_notes_backend(command.notes_backend, settings.notes_backend)
            resolve_note_style(command.note_style, settings.note_style)
            resolve_transcription_settings(
                settings,
                command.transcription_backend,
                command.transcription_model,
                command.transcription_prompt,
                command.local_whisper_model,
                command.local_whisper_language,
            )
        except (RuntimeError, ValueError) as exc:
            raise ApplicationError(400, str(exc)) from exc

        task_id = command.task_id or str(uuid4())
        set_task_status(
            task_id,
            "queued",
            url=command.url,
            delete_video_after_completion=command.delete_video_after_completion,
        )
        history = HistoryStore(settings.database_path)
        queued_task = get_task(task_id)
        if queued_task is not None:
            history.upsert_task(queued_task)

        arguments = (
            task_id,
            command.url,
            command.notes_dir,
            command.notes_backend,
            command.note_style,
            command.ollama_model,
            command.reuse_task_id,
            command.force_download,
            command.delete_video_after_completion,
            command.transcription_backend,
            command.transcription_model,
            command.transcription_prompt,
            command.local_whisper_model,
            command.local_whisper_language,
        )
        try:
            queue_backend = enqueue_video_processing(
                command.local_scheduler,
                process_video,
                settings,
                *arguments,
            )
        except Exception as exc:
            message = f"任务队列暂时不可用：{exc}"
            set_task_status(task_id, "failed", message, log_level="error", error=message)
            failed_task = get_task(task_id)
            if failed_task is not None:
                history.upsert_task(failed_task)
            raise ApplicationError(503, message) from exc

        return {
            "task_id": task_id,
            "status": "queued",
            "queue_backend": queue_backend,
            "status_url": f"/task_status/{task_id}",
        }


class RunVideoProcessingHandler:
    async def handle(self, command: RunVideoProcessingCommand) -> None:
        await process_video(*command.arguments)


class WorkerProbeHandler:
    def handle(self, command: WorkerProbeCommand) -> dict:
        return {"worker": "ready", "mediator": "ready", "value": command.value}


class GetTaskHandler:
    def handle(self, query: GetTaskQuery) -> dict:
        task = get_task(query.task_id)
        if task is None:
            raise ApplicationError(404, "找不到任务。")
        return task


class ListTasksHandler:
    def handle(self, _query: ListTasksQuery) -> list[dict]:
        return list_tasks()
