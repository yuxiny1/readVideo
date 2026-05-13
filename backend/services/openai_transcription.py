import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import wave

from openai import OpenAI

try:
    from moviepy import AudioFileClip
except ImportError:  # moviepy<2 compatibility
    from moviepy.editor import AudioFileClip


DEFAULT_TRANSCRIPTION_MODEL = "whisper-1"


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    transcription_path: str
    chunk_count: int


class AudioTranscription:
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_TRANSCRIPTION_MODEL,
        language: str = "auto",
        prompt: str = "",
        client=None,
    ):
        self.api_key = api_key
        self.model = model
        self.language = language
        self.prompt = prompt
        self.client = client or OpenAI(api_key=api_key)

    def split_audio_by_duration(self, audio_path: str, chunk_duration_sec: int) -> list:
        """
        Split the audio file into chunks based on duration in seconds.
        """
        if chunk_duration_sec <= 0:
            raise ValueError("chunk_duration_sec must be greater than 0")

        chunks = []
        audio_file_path = Path(audio_path)
        output_dir = audio_file_path.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        base_name = audio_file_path.stem

        with wave.open(str(audio_file_path), "rb") as wave_file:
            params = wave_file.getparams()
            frames_per_chunk = wave_file.getframerate() * chunk_duration_sec

            chunk_index = 0
            while True:
                chunk_data = wave_file.readframes(frames_per_chunk)
                if not chunk_data:
                    break

                chunk_file_path = output_dir / f"{base_name}_chunk_{chunk_index}.wav"
                with wave.open(str(chunk_file_path), "wb") as chunk:
                    chunk.setparams(params)
                    chunk.writeframes(chunk_data)

                chunks.append(str(chunk_file_path))
                chunk_index += 1

        return chunks

    def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Transcribe audio using the OpenAI audio transcription API.
        """
        with open(audio_file_path, "rb") as audio_file:
            payload = {"model": self.model, "file": audio_file}
            if self.language and self.language != "auto":
                payload["language"] = self.language
            if self.prompt:
                payload["prompt"] = self.prompt
            transcription = self.client.audio.transcriptions.create(**payload)

        if isinstance(transcription, str):
            return transcription

        text = getattr(transcription, "text", None)
        if text is not None:
            return text

        if isinstance(transcription, dict):
            return transcription.get("text", "")

        raise TypeError("OpenAI transcription response did not include text.")

    def save_transcription(self, text: str, original_video_path: str) -> str:
        """
        Save the transcribed text next to the original video file.
        """
        video_path = Path(original_video_path)
        output_file_path = video_path.with_name(f"{video_path.stem}_transcription.txt")

        with open(output_file_path, "w", encoding="utf-8") as text_file:
            text_file.write(text)

        return str(output_file_path)

    def delete_chunk_files(self, chunks: list):
        """
        Delete temporary chunk files.
        """
        for chunk_path in chunks:
            try:
                os.remove(chunk_path)
            except FileNotFoundError:
                pass

    def process_video(self, video_file_path: str, chunk_duration_sec: int = 180):
        """
        Convert a video to audio, split it into chunks, transcribe, and clean up.
        """
        video_path = Path(video_file_path)
        if not video_path.is_file():
            raise FileNotFoundError(f"Video file not found: {video_file_path}")

        audio_file_path = video_path.with_suffix(".wav")
        audio_chunks = []

        try:
            with AudioFileClip(str(video_path)) as audio:
                audio.write_audiofile(
                    str(audio_file_path),
                    fps=16000,
                    nbytes=2,
                    codec="pcm_s16le",
                    logger=None,
                )

            audio_chunks = self.split_audio_by_duration(str(audio_file_path), chunk_duration_sec)
            transcriptions = []
            for chunk_path in audio_chunks:
                transcription_text = self.transcribe_audio(chunk_path).strip()
                if transcription_text:
                    transcriptions.append(transcription_text)

            full_transcription = "\n\n".join(transcriptions)
            transcription_path = self.save_transcription(full_transcription, str(video_path))
            return TranscriptionResult(
                text=full_transcription,
                transcription_path=transcription_path,
                chunk_count=len(audio_chunks),
            )
        finally:
            self.delete_chunk_files(audio_chunks)
            if audio_file_path.exists():
                audio_file_path.unlink()
