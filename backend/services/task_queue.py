import asyncio
from collections.abc import Callable

from backend.core.config import Settings


DEFAULT_JOB_TIMEOUT_SECONDS = 60 * 60 * 6


def enqueue_video_processing(
    local_scheduler: Callable[..., None],
    processor: Callable,
    settings: Settings,
    *args,
) -> str:
    if not settings.redis_url:
        local_scheduler(processor, *args)
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
    from backend.application.container import get_mediator
    from backend.application.messages.tasks import RunVideoProcessingCommand

    asyncio.run(get_mediator().send(RunVideoProcessingCommand(tuple(args))))


def run_worker_probe(value: str) -> dict:
    from backend.application.container import get_mediator
    from backend.application.messages.tasks import WorkerProbeCommand

    return asyncio.run(get_mediator().send(WorkerProbeCommand(value)))
