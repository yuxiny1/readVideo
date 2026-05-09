import asyncio
import logging
from typing import Optional
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field, HttpUrl

from audioTranscription import AudioTranscription
from config import load_settings
from yt_dl import download_video


logger = logging.getLogger(__name__)
app = FastAPI(title="readVideo")
TASKS = {}


class ProcessVideoRequest(BaseModel):
    url: HttpUrl
    task_id: Optional[str] = Field(default=None, min_length=1)


def set_task_status(task_id: str, status: str, **details):
    TASKS[task_id] = {"task_id": task_id, "status": status, **details}


async def process_video(task_id: str, url: str):
    try:
        settings = load_settings()
        set_task_status(task_id, "downloading", url=url)

        downloaded_file_path = await asyncio.to_thread(download_video, url, settings.download_dir)
        set_task_status(task_id, "transcribing", url=url, video_path=downloaded_file_path)

        transcription_service = AudioTranscription(
            api_key=settings.openai_api_key,
            model=settings.transcription_model,
        )
        result = await asyncio.to_thread(
            transcription_service.process_video,
            downloaded_file_path,
            settings.chunk_seconds,
        )

        set_task_status(
            task_id,
            "completed",
            url=url,
            video_path=downloaded_file_path,
            transcription_path=result.transcription_path,
            chunk_count=result.chunk_count,
        )
    except Exception as exc:
        logger.exception("Task %s failed", task_id)
        set_task_status(task_id, "failed", url=url, error=str(exc))


@app.post("/process_video/")
async def create_task(request: ProcessVideoRequest, background_tasks: BackgroundTasks):
    try:
        load_settings()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    task_id = request.task_id or str(uuid4())
    set_task_status(task_id, "queued", url=str(request.url))
    background_tasks.add_task(process_video, task_id, str(request.url))

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


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
