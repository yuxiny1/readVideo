import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(PROJECT_ROOT / "config" / ".env", override=True)


@dataclass(frozen=True)
class Settings:
    transcription_backend: str = "local"
    openai_api_key: Optional[str] = None
    download_dir: str = "downloads/youtube_videos"
    transcription_model: str = "gpt-4o-mini-transcribe"
    chunk_seconds: int = 180
    local_whisper_cli: str = "whisper-cli"
    local_whisper_model: str = "models/ggml-large-v3-turbo.bin"
    local_whisper_language: str = "auto"
    local_whisper_prompt: str = ""
    local_whisper_audio_filter: str = "highpass=f=80,lowpass=f=8000,loudnorm=I=-16:TP=-1.5:LRA=11"
    notes_dir: str = "notes"
    notes_backend: str = "ollama"
    ollama_model: str = "qwen2.5:32b"
    ollama_url: str = "http://127.0.0.1:11434/api/generate"
    database_path: str = "readvideo.sqlite3"


def load_openai_api_key(config_path: str = "apiKey.json", required: bool = True) -> Optional[str]:
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key

    key_file = Path(config_path)
    if not key_file.is_absolute():
        key_file = PROJECT_ROOT / key_file
    if key_file.exists():
        with open(key_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        api_key = config.get("apiKey") or config.get("OPENAI_API_KEY")
        if api_key:
            return api_key

    if required:
        raise RuntimeError("Set OPENAI_API_KEY or create apiKey.json with an apiKey value.")
    return None


def _load_chunk_seconds(raw_value: Optional[str]) -> int:
    if raw_value is None:
        return 180

    try:
        chunk_seconds = int(raw_value)
    except ValueError as exc:
        raise RuntimeError("READVIDEO_CHUNK_SECONDS must be an integer.") from exc

    if chunk_seconds <= 0:
        raise RuntimeError("READVIDEO_CHUNK_SECONDS must be greater than 0.")

    return chunk_seconds


def _default_local_whisper_model() -> str:
    configured_model = os.getenv("READVIDEO_LOCAL_WHISPER_MODEL")
    if configured_model:
        return configured_model

    for model_path in (
        "models/ggml-large-v3-turbo.bin",
        "models/ggml-medium.bin",
        "models/ggml-small.bin",
        "models/ggml-base.bin",
    ):
        if (PROJECT_ROOT / model_path).is_file():
            return model_path
    return "models/ggml-large-v3-turbo.bin"


def load_settings() -> Settings:
    transcription_backend = os.getenv("READVIDEO_TRANSCRIPTION_BACKEND", "local").lower()
    if transcription_backend not in {"local", "openai"}:
        raise RuntimeError("READVIDEO_TRANSCRIPTION_BACKEND must be local or openai.")

    notes_backend = os.getenv("READVIDEO_NOTES_BACKEND", "ollama").lower()
    if notes_backend not in {"extractive", "ollama"}:
        raise RuntimeError("READVIDEO_NOTES_BACKEND must be extractive or ollama.")

    return Settings(
        transcription_backend=transcription_backend,
        openai_api_key=load_openai_api_key(required=transcription_backend == "openai"),
        download_dir=os.getenv("READVIDEO_DOWNLOAD_DIR", "downloads/youtube_videos"),
        transcription_model=os.getenv("OPENAI_TRANSCRIPTION_MODEL", "gpt-4o-mini-transcribe"),
        chunk_seconds=_load_chunk_seconds(os.getenv("READVIDEO_CHUNK_SECONDS")),
        local_whisper_cli=os.getenv("READVIDEO_LOCAL_WHISPER_CLI", "whisper-cli"),
        local_whisper_model=_default_local_whisper_model(),
        local_whisper_language=os.getenv("READVIDEO_LOCAL_WHISPER_LANGUAGE", "auto"),
        local_whisper_prompt=os.getenv("READVIDEO_LOCAL_WHISPER_PROMPT", ""),
        local_whisper_audio_filter=os.getenv(
            "READVIDEO_LOCAL_WHISPER_AUDIO_FILTER",
            "highpass=f=80,lowpass=f=8000,loudnorm=I=-16:TP=-1.5:LRA=11",
        ),
        notes_dir=os.getenv("READVIDEO_NOTES_DIR", "notes"),
        notes_backend=notes_backend,
        ollama_model=os.getenv("READVIDEO_OLLAMA_MODEL", "qwen2.5:32b"),
        ollama_url=os.getenv("READVIDEO_OLLAMA_URL", "http://127.0.0.1:11434/api/generate"),
        database_path=os.getenv("READVIDEO_DATABASE_PATH", "readvideo.sqlite3"),
    )
