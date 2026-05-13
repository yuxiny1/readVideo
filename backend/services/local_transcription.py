import re
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import wave


DEFAULT_AUDIO_FILTER = "highpass=f=80,lowpass=f=8000,loudnorm=I=-16:TP=-1.5:LRA=11"


@dataclass(frozen=True)
class LocalTranscriptionResult:
    text: str
    transcription_path: str
    model_path: str
    chunk_count: int


class LocalWhisperTranscription:
    def __init__(
        self,
        whisper_cli: str = "whisper-cli",
        model_path: str = "models/ggml-small.bin",
        language: str = "auto",
        prompt: str = "",
        audio_filter: str = DEFAULT_AUDIO_FILTER,
        chunk_seconds: int = 60,
    ):
        self.whisper_cli = whisper_cli
        self.model_path = model_path
        self.language = language or "auto"
        self.prompt = prompt
        self.audio_filter = audio_filter
        self.chunk_seconds = chunk_seconds

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
        chunk_paths = []
        chunk_output_paths = []

        try:
            if transcript_path.exists():
                transcript_path.unlink()

            _run_command(_build_ffmpeg_command(video_path, audio_path, self.audio_filter))
            chunk_paths = _split_wav_by_duration(audio_path, self.chunk_seconds)
            supported_flags = _supported_whisper_flags(self.whisper_cli)
            transcriptions = []

            for index, chunk_path in enumerate(chunk_paths):
                chunk_output_base = output_base.with_name(f"{output_base.name}_chunk_{index:04d}")
                chunk_transcript_path = chunk_output_base.with_suffix(".txt")
                chunk_output_paths.append(chunk_transcript_path)

                _run_command(
                    _build_whisper_command(
                        self.whisper_cli,
                        self.model_path,
                        chunk_path,
                        self.language,
                        chunk_output_base,
                        self.prompt,
                        supported_flags,
                    )
                )

                if not chunk_transcript_path.exists():
                    raise RuntimeError(f"Whisper did not create transcript chunk: {chunk_transcript_path}")
                chunk_text = _normalize_whisper_text(chunk_transcript_path.read_text(encoding="utf-8")).strip()
                if chunk_text:
                    transcriptions.append(chunk_text)

            text = "\n\n".join(transcriptions)
            if text:
                text += "\n"
            transcript_path.write_text(text, encoding="utf-8")
            return LocalTranscriptionResult(
                text=text,
                transcription_path=str(transcript_path),
                model_path=self.model_path,
                chunk_count=len(chunk_paths),
            )
        finally:
            for temporary_path in [*chunk_paths, *chunk_output_paths]:
                if temporary_path.exists():
                    temporary_path.unlink()
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
    lines = _drop_repetitive_hallucinations(lines)
    return "\n".join(lines) + ("\n" if lines else "")


def _drop_repetitive_hallucinations(lines: list[str]) -> list[str]:
    cleaned = []
    index = 0
    while index < len(lines):
        key = _latin_noise_key(lines[index])
        if key is None:
            cleaned.append(lines[index])
            index += 1
            continue

        end = index + 1
        while end < len(lines) and _latin_noise_key(lines[end]) == key:
            end += 1

        if end - index < 3:
            cleaned.extend(lines[index:end])
        index = end
    return cleaned


def _latin_noise_key(line: str) -> str | None:
    normalized = re.sub(r"[^A-Za-z\s]", "", line).strip().lower()
    if not normalized:
        return None

    tokens = normalized.split()
    if len(tokens) == 1 and len(tokens[0]) >= 5:
        return tokens[0][:8]

    if len(tokens) >= 4 and len(set(tokens)) <= 2:
        return " ".join(sorted(set(tokens)))

    return None


def _split_wav_by_duration(audio_path: Path, chunk_seconds: int) -> list[Path]:
    if chunk_seconds <= 0:
        raise ValueError("chunk_seconds must be greater than 0")

    chunk_paths = []
    with wave.open(str(audio_path), "rb") as wave_file:
        params = wave_file.getparams()
        frames_per_chunk = int(wave_file.getframerate() * chunk_seconds)

        chunk_index = 0
        while True:
            chunk_data = wave_file.readframes(frames_per_chunk)
            if not chunk_data:
                break

            chunk_path = audio_path.with_name(f"{audio_path.stem}_chunk_{chunk_index:04d}.wav")
            with wave.open(str(chunk_path), "wb") as chunk:
                chunk.setparams(params)
                chunk.writeframes(chunk_data)

            chunk_paths.append(chunk_path)
            chunk_index += 1

    return chunk_paths


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
