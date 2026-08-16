from backend.application.errors import ApplicationError
from backend.application.messages.models import (
    DownloadWhisperModelCommand,
    GetMlxStatusQuery,
    ListOllamaModelsQuery,
    ListTranscriptionModelsQuery,
    PullOllamaModelCommand,
)
from backend.core.config import load_settings
from backend.services.ollama_models import (
    list_installed_models,
    list_ollama_models,
    pull_model,
    pull_ollama_model,
    recommended_models,
)
from backend.services.mlx_client import inspect_mlx_server
from backend.services.mlx_whisper_models import (
    download_mlx_whisper_model,
    inspect_mlx_whisper_runtime,
    list_installed_mlx_whisper_models,
    recommended_mlx_whisper_models,
)
from backend.services.whisper_models import (
    download_whisper_model,
    list_installed_whisper_models,
    recommended_whisper_models,
)


OPENAI_TRANSCRIPTION_MODELS = [
    {"name": "gpt-4o-mini-transcribe", "label": "GPT-4o Mini 转录", "notes": "成本较低的 OpenAI 转录模型。"},
    {"name": "gpt-4o-transcribe", "label": "GPT-4o 转录", "notes": "质量更高的 OpenAI 转录模型。"},
    {"name": "whisper-1", "label": "Whisper 1", "notes": "旧版 OpenAI Whisper 模型。"},
]
TRANSCRIPTION_LANGUAGES = [
    {"code": "auto", "label": "自动检测"},
    {"code": "zh", "label": "中文"},
    {"code": "en", "label": "英语"},
    {"code": "ja", "label": "日语"},
    {"code": "ko", "label": "韩语"},
    {"code": "es", "label": "西班牙语"},
    {"code": "fr", "label": "法语"},
]


class ListOllamaModelsHandler:
    def handle(self, _query: ListOllamaModelsQuery) -> dict:
        settings = load_settings()
        installed = list_installed_models()
        try:
            models = list_ollama_models(settings.ollama_url)
        except RuntimeError as exc:
            return {
                "status": "error",
                "error": str(exc),
                "default_model": settings.ollama_model,
                "recommended": recommended_models(),
                "installed": installed,
                "models": [],
            }
        return {
            "status": "ok",
            "default_model": settings.ollama_model,
            "recommended": recommended_models(),
            "installed": installed,
            "models": [model.__dict__ for model in models],
        }


class GetMlxStatusHandler:
    def handle(self, _query: GetMlxStatusQuery) -> dict:
        settings = load_settings()
        try:
            status = inspect_mlx_server(settings.mlx_url)
        except RuntimeError as exc:
            return {
                "status": "error",
                "error": str(exc),
                "default_model": settings.mlx_model,
                "models": [],
                "start_command": _mlx_start_command(settings.mlx_model),
            }
        return {
            "status": "ok",
            "default_model": settings.mlx_model,
            "models": status.models,
            "start_command": _mlx_start_command(settings.mlx_model),
        }


def _mlx_start_command(model: str) -> str:
    return f"~/mlx-env/bin/mlx_lm.server --model {model} --host 127.0.0.1 --port 8080"


class PullOllamaModelHandler:
    def handle(self, command: PullOllamaModelCommand) -> dict:
        settings = load_settings()
        try:
            result = pull_ollama_model(command.model, settings.ollama_url)
        except RuntimeError as exc:
            try:
                result = {"output": pull_model(command.model)}
            except RuntimeError as fallback_exc:
                raise ApplicationError(400, str(fallback_exc)) from exc
        return {"status": "ok", "model": command.model, "result": result}


class ListTranscriptionModelsHandler:
    def handle(self, _query: ListTranscriptionModelsQuery) -> dict:
        settings = load_settings()
        return {
            "whisper": recommended_whisper_models(settings.local_whisper_model),
            "installed_whisper": list_installed_whisper_models(settings.local_whisper_model),
            "mlx_whisper": recommended_mlx_whisper_models(),
            "installed_mlx_whisper": list_installed_mlx_whisper_models(),
            "mlx_whisper_runtime": inspect_mlx_whisper_runtime(settings.mlx_whisper_python),
            "openai": OPENAI_TRANSCRIPTION_MODELS,
            "languages": TRANSCRIPTION_LANGUAGES,
        }


class DownloadWhisperModelHandler:
    def handle(self, command: DownloadWhisperModelCommand) -> dict:
        try:
            if command.model.startswith("mlx-community/"):
                settings = load_settings()
                return download_mlx_whisper_model(command.model, settings.mlx_whisper_python)
            return download_whisper_model(command.model, load_settings().local_whisper_model)
        except ValueError as exc:
            raise ApplicationError(404, str(exc)) from exc
        except (OSError, RuntimeError) as exc:
            raise ApplicationError(400, str(exc)) from exc
