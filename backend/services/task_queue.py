import asyncio
from collections.abc import Callable

from fastapi import BackgroundTasks

from backend.core.config import Settings


DEFAULT_JOB_TIMEOUT_SECONDS = 60 * 60 * 6


def enqueue_video_processing(
    background_tasks: BackgroundTasks,
    processor: Callable,
    settings: Settings,
    *args,
) -> str:
    if not settings.redis_url:
        background_tasks.add_task(processor, *args)
        return "local"

    from redis import Redis
    from rq import Queue

    connection = Redis.from_url(settings.redis_url)
    queue = Queue(settings.task_queue_name, connection=connection)
    queue.enqueue(
        run_video_job,
        *args,
        job_id=str(args[0]),
        job_timeout=DEFAULT_JOB_TIMEOUT_SECONDS,
        result_ttl=86400,
        failure_ttl=604800,
    )
    return "redis"


def run_video_job(*args) -> None:
    from backend.services.video_processor import process_video

    asyncio.run(process_video(*args))
