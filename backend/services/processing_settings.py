from dataclasses import dataclass, replace
from typing import Optional

from backend.core.config import Settings, load_openai_api_key


NOTES_BACKENDS = {"extractive", "ollama", "mlx"}
NOTE_STYLES = {"detailed", "commercial"}
TRANSCRIPTION_BACKENDS = {"local", "mlx", "openai"}


@dataclass(frozen=True)
class ProcessingPlan:
    settings: Settings
    notes_dir: str
    notes_backend: str
    note_style: str
    ollama_model: str
    mlx_model: str

    def task_metadata(self, delete_video_after_completion: bool) -> dict:
        settings = self.settings
        metadata = {
            "notes_backend": self.notes_backend,
            "note_style": self.note_style,
            "ollama_model": self.ollama_model if self.notes_backend == "ollama" else None,
            "transcription_backend": settings.transcription_backend,
            "transcription_model": settings.transcription_model if settings.transcription_backend == "openai" else None,
            "local_whisper_model": settings.local_whisper_model if settings.transcription_backend == "local" else None,
            "local_whisper_language": settings.local_whisper_language if settings.transcription_backend in {"local", "mlx"} else None,
            "delete_video_after_completion": delete_video_after_completion,
        }
        if self.notes_backend == "mlx":
            metadata["mlx_model"] = self.mlx_model
        if settings.transcription_backend == "mlx":
            metadata["mlx_whisper_model"] = settings.mlx_whisper_model
        return metadata


def resolve_processing_plan(
    settings: Settings,
    notes_dir: Optional[str] = None,
    notes_backend: Optional[str] = None,
    note_style: Optional[str] = None,
    ollama_model: Optional[str] = None,
    transcription_backend: Optional[str] = None,
    transcription_model: Optional[str] = None,
    transcription_prompt: Optional[str] = None,
    local_whisper_model: Optional[str] = None,
    local_whisper_language: Optional[str] = None,
    mlx_model: Optional[str] = None,
    mlx_whisper_model: Optional[str] = None,
) -> ProcessingPlan:
    resolved_notes_backend = _choice(
        notes_backend,
        settings.notes_backend,
        NOTES_BACKENDS,
        "笔记引擎无效，请选择本地提取式笔记或 Ollama 本地大模型，也可以选择 MLX 本地大模型。",
    )
    resolved_note_style = _choice(
        note_style,
        settings.note_style,
        NOTE_STYLES,
        "笔记风格无效，请选择详细笔记或商业分析。",
    )
    resolved_transcription_backend = _choice(
        transcription_backend,
        settings.transcription_backend,
        TRANSCRIPTION_BACKENDS,
        "转录引擎无效，请选择 MLX Whisper、whisper.cpp 或 OpenAI 转录。",
    )

    openai_api_key = settings.openai_api_key
    if resolved_transcription_backend == "openai" and not openai_api_key:
        openai_api_key = load_openai_api_key(required=True)

    resolved_settings = replace(
        settings,
        transcription_backend=resolved_transcription_backend,
        openai_api_key=openai_api_key,
        transcription_model=transcription_model or settings.transcription_model,
        local_whisper_model=local_whisper_model or settings.local_whisper_model,
        mlx_whisper_model=mlx_whisper_model or settings.mlx_whisper_model,
        local_whisper_language=local_whisper_language or settings.local_whisper_language,
        local_whisper_prompt=(transcription_prompt or settings.local_whisper_prompt or "").strip(),
    )
    return ProcessingPlan(
        settings=resolved_settings,
        notes_dir=notes_dir or settings.notes_dir,
        notes_backend=resolved_notes_backend,
        note_style=resolved_note_style,
        ollama_model=ollama_model or settings.ollama_model,
        mlx_model=mlx_model or settings.mlx_model,
    )


def _choice(requested: Optional[str], default: str, allowed: set[str], message: str) -> str:
    value = (requested or default).lower()
    if value not in allowed:
        raise RuntimeError(message)
    return value
