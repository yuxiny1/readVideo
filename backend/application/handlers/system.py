from backend.application.handlers.models import OPENAI_TRANSCRIPTION_MODELS
from backend.application.messages.system import AppConfigQuery, HealthQuery, ReadinessQuery
from backend.core.config import load_settings
from backend.services.ollama_models import recommended_models
from backend.services.platform_health import inspect_platform


class HealthHandler:
    def handle(self, _query: HealthQuery) -> dict:
        return {"status": "ok"}


class ReadinessHandler:
    def handle(self, _query: ReadinessQuery) -> dict:
        return inspect_platform(load_settings())


class AppConfigHandler:
    def handle(self, _query: AppConfigQuery) -> dict:
        settings = load_settings()
        return {
            "transcription_backend": settings.transcription_backend,
            "download_dir": settings.download_dir,
            "notes_dir": settings.notes_dir,
            "notes_backend": settings.notes_backend,
            "note_style": settings.note_style,
            "ollama_model": settings.ollama_model,
            "ollama_model_options": recommended_models(),
            "mlx_model": settings.mlx_model,
            "mlx_url": settings.mlx_url,
            "local_whisper_model": settings.local_whisper_model,
            "local_whisper_language": settings.local_whisper_language,
            "transcription_model": settings.transcription_model,
            "transcription_prompt": settings.local_whisper_prompt,
            "openai_transcription_model_options": OPENAI_TRANSCRIPTION_MODELS,
        }
