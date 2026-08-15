from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class StartVideoProcessingCommand:
    local_scheduler: Callable[..., None]
    task_id: Optional[str]
    url: str
    notes_dir: Optional[str]
    notes_backend: Optional[str]
    note_style: Optional[str]
    ollama_model: Optional[str]
    mlx_model: Optional[str]
    reuse_task_id: Optional[str]
    force_download: bool
    delete_video_after_completion: bool
    transcription_backend: Optional[str]
    transcription_model: Optional[str]
    transcription_prompt: Optional[str]
    local_whisper_model: Optional[str]
    local_whisper_language: Optional[str]


@dataclass(frozen=True)
class RunVideoProcessingCommand:
    arguments: tuple[Any, ...]


@dataclass(frozen=True)
class WorkerProbeCommand:
    value: str


@dataclass(frozen=True)
class GetTaskQuery:
    task_id: str


@dataclass(frozen=True)
class ListTasksQuery:
    pass
