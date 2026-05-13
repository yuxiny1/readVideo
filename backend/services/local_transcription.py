import re
import shutil
import subprocess
from functools import lru_cache
from dataclasses import dataclass
from pathlib import Path


DEFAULT_AUDIO_FILTER = "highpass=f=80,lowpass=f=8000,loudnorm=I=-16:TP=-1.5:LRA=11"


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
        language: str = "auto",
        prompt: str = "",
        audio_filter: str = DEFAULT_AUDIO_FILTER,
    ):
        self.whisper_cli = whisper_cli
        self.model_path = model_path
        self.language = language or "auto"
        self.prompt = prompt
        self.audio_filter = audio_filter

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
            _run_command(_build_ffmpeg_command(video_path, audio_path, self.audio_filter))
            _run_command(
                _build_whisper_command(
                    self.whisper_cli,
                    self.model_path,
                    audio_path,
                    self.language,
                    output_base,
                    self.prompt,
                    _supported_whisper_flags(self.whisper_cli),
                )
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


def _build_ffmpeg_command(video_path: Path, audio_path: Path, audio_filter: str = DEFAULT_AUDIO_FILTER) -> list[str]:
    command = [
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
    ]
    if audio_filter:
        command.extend(["-af", audio_filter])
    command.extend(["-c:a", "pcm_s16le", str(audio_path)])
    return command


def _build_whisper_command(
    whisper_cli: str,
    model_path: str,
    audio_path: Path,
    language: str,
    output_base: Path,
    prompt: str = "",
    supported_flags: set[str] | None = None,
) -> list[str]:
    flags = supported_flags or set()
    command = [
        whisper_cli,
        "-m",
        model_path,
        "-f",
        str(audio_path),
        "-l",
        language or "auto",
        "-otxt",
        "-of",
        str(output_base),
    ]
    if "-nt" in flags or "--no-timestamps" in flags:
        command.append("-nt")
    if prompt and "--prompt" in flags:
        command.extend(["--prompt", prompt])
    if "-sns" in flags or "--suppress-nst" in flags:
        command.append("-sns")
    return command


@lru_cache(maxsize=4)
def _supported_whisper_flags(whisper_cli: str) -> set[str]:
    try:
        result = subprocess.run([whisper_cli, "--help"], capture_output=True, text=True, check=False)
    except OSError:
        return set()
    help_text = f"{result.stdout}\n{result.stderr}"
    return set(re.findall(r"(?<!\w)(?:--?[A-Za-z][A-Za-z0-9-]*)", help_text))


def _run_command(command: list[str]):
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        output = (result.stderr or result.stdout or "").strip()
        if len(output) > 2000:
            output = output[-2000:]
        raise RuntimeError(f"Command failed: {' '.join(command[:2])}\n{output}")
