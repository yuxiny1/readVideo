import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LocalTranscriptionResult:
    text: str
    transcription_path: str
    model_path: str


class LocalWhisperTranscription:
    def __init__(
        self,
        whisper_cli: str = "whisper-cli",
        model_path: str = "models/ggml-small.bin",
        language: str = "zh",
    ):
        self.whisper_cli = whisper_cli
        self.model_path = model_path
        self.language = language

    def _validate(self):
        if shutil.which("ffmpeg") is None:
            raise RuntimeError("ffmpeg was not found. Install it with: brew install ffmpeg")

        if shutil.which(self.whisper_cli) is None:
            raise RuntimeError(
                f"{self.whisper_cli} was not found. Install it with: brew install whisper-cpp"
            )

        if not Path(self.model_path).is_file():
            raise RuntimeError(
                f"Local Whisper model not found at {self.model_path}. "
                "Download one from https://huggingface.co/ggerganov/whisper.cpp/tree/main"
            )

    def process_video(self, video_file_path: str) -> LocalTranscriptionResult:
        self._validate()

        video_path = Path(video_file_path)
        if not video_path.is_file():
            raise FileNotFoundError(f"Video file not found: {video_file_path}")

        audio_path = video_path.with_suffix(".local-whisper.wav")
        output_base = video_path.with_name(f"{video_path.stem}_transcription")
        transcript_path = output_base.with_suffix(".txt")

        try:
            _run_command(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    str(video_path),
                    "-vn",
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    str(audio_path),
                ]
            )

            _run_command(
                [
                    self.whisper_cli,
                    "-m",
                    self.model_path,
                    "-f",
                    str(audio_path),
                    "-l",
                    self.language,
                    "-otxt",
                    "-of",
                    str(output_base),
                ]
            )

            text = transcript_path.read_text(encoding="utf-8")
            text = _normalize_whisper_text(text)
            transcript_path.write_text(text, encoding="utf-8")
            return LocalTranscriptionResult(
                text=text,
                transcription_path=str(transcript_path),
                model_path=self.model_path,
            )
        finally:
            if audio_path.exists():
                audio_path.unlink()


def _normalize_whisper_text(text: str) -> str:
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"\s+", " ", line)
        lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def _run_command(command: list[str]):
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        output = (result.stderr or result.stdout or "").strip()
        if len(output) > 2000:
            output = output[-2000:]
        raise RuntimeError(f"Command failed: {' '.join(command[:2])}\n{output}")
