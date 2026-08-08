from dataclasses import dataclass
from typing import Optional

from backend.core.config import Settings
from backend.services.local_transcription import LocalWhisperTranscription
from backend.services.openai_transcription import AudioTranscription


@dataclass(frozen=True)
class ExistingTranscriptionResult:
    text: str
    transcription_path: str
    chunk_count: Optional[int] = None
    recovered_encoding: bool = False
    decode_error: str = ""


def transcribe_video(video_path: str, settings: Settings):
    if settings.transcription_backend == "local":
        transcriber = LocalWhisperTranscription(
            whisper_cli=settings.local_whisper_cli,
            model_path=settings.local_whisper_model,
            language=settings.local_whisper_language,
            prompt=settings.local_whisper_prompt,
            audio_filter=settings.local_whisper_audio_filter,
        )
        return transcriber.process_video(video_path)

    transcriber = AudioTranscription(
        api_key=settings.openai_api_key,
        model=settings.transcription_model,
        language=settings.local_whisper_language,
        prompt=settings.local_whisper_prompt,
    )
    return transcriber.process_video(video_path, settings.chunk_seconds)
