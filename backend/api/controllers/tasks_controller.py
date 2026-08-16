from fastapi import APIRouter, BackgroundTasks

from backend.api.schemas import ProcessVideoRequest
from backend.application import get_mediator
from backend.application.messages.tasks import GetTaskQuery, ListTasksQuery, StartVideoProcessingCommand


router = APIRouter()


@router.post("/process_video/")
async def create_task(request: ProcessVideoRequest, background_tasks: BackgroundTasks):
    command = StartVideoProcessingCommand(
        local_scheduler=background_tasks.add_task,
        task_id=request.task_id,
        url=str(request.url),
        notes_dir=request.notes_dir,
        notes_backend=request.notes_backend,
        note_style=request.note_style,
        ollama_model=request.ollama_model,
        mlx_model=request.mlx_model,
        reuse_task_id=request.reuse_task_id,
        force_download=request.force_download,
        delete_video_after_completion=request.delete_video_after_completion,
        transcription_backend=request.transcription_backend,
        transcription_model=request.transcription_model,
        transcription_prompt=request.transcription_prompt,
        local_whisper_model=request.local_whisper_model,
        local_whisper_language=request.local_whisper_language,
        mlx_whisper_model=request.mlx_whisper_model,
    )
    return await get_mediator().send(command)


@router.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    return await get_mediator().send(GetTaskQuery(task_id))


@router.get("/tasks")
async def get_tasks():
    return await get_mediator().send(ListTasksQuery())
