import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    download_dir: str = "downloads/youtube_videos"
    transcription_model: str = "whisper-1"
    chunk_seconds: int = 180


def load_openai_api_key(config_path: str = "apiKey.json") -> str:
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key

    key_file = Path(config_path)
    if key_file.exists():
        with open(key_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        api_key = config.get("apiKey") or config.get("OPENAI_API_KEY")
        if api_key:
            return api_key

    raise RuntimeError("Set OPENAI_API_KEY or create apiKey.json with an apiKey value.")


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


def load_settings() -> Settings:
    return Settings(
        openai_api_key=load_openai_api_key(),
        download_dir=os.getenv("READVIDEO_DOWNLOAD_DIR", "downloads/youtube_videos"),
        transcription_model=os.getenv("OPENAI_TRANSCRIPTION_MODEL", "whisper-1"),
        chunk_seconds=_load_chunk_seconds(os.getenv("READVIDEO_CHUNK_SECONDS")),
    )
