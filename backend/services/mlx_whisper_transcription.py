import subprocess
from pathlib import Path

from backend.services.downloader import clean_filename_part
from backend.services.local_transcription import LocalTranscriptionResult, read_transcript_text
from backend.services.media_audio import (
    DEFAULT_AUDIO_FILTER,
    build_ffmpeg_command,
    decode_process_output,
    run_command,
)
from backend.services.mlx_whisper_models import inspect_mlx_whisper_runtime


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class MlxWhisperTranscription:
    def __init__(
        self,
        python_executable: str,
        model: str,
        language: str = "auto",
        prompt: str = "",
        audio_filter: str = DEFAULT_AUDIO_FILTER,
    ):
        self.python_executable = python_executable
        self.model = model
        self.language = language or "auto"
        self.prompt = prompt
        self.audio_filter = audio_filter

    def _validated_python(self) -> str:
        runtime = inspect_mlx_whisper_runtime(self.python_executable)
        if not runtime["available"]:
            raise RuntimeError(runtime["error"])
        return runtime["python"]

    def process_video(self, video_file_path: str) -> LocalTranscriptionResult:
        python_executable = self._validated_python()
        video_path = Path(video_file_path)
        if not video_path.is_file():
            raise FileNotFoundError(f"找不到视频文件：{video_file_path}")

        audio_path = video_path.with_suffix(".mlx-whisper.wav")
        transcript_path = video_path.with_name(
            f"{clean_filename_part(video_path.stem)}_transcription.txt"
        )
        try:
            run_command(build_ffmpeg_command(video_path, audio_path, self.audio_filter))
            _run_mlx_whisper(
                python_executable=python_executable,
                audio_path=audio_path,
                transcript_path=transcript_path,
                model=self.model,
                language=self.language,
                prompt=self.prompt,
            )
            transcript = read_transcript_text(transcript_path)
            return LocalTranscriptionResult(
                text=transcript.text,
                transcription_path=str(transcript_path),
                model_path=self.model,
                recovered_encoding=transcript.recovered_encoding,
                decode_error=transcript.decode_error,
            )
        finally:
            if audio_path.exists():
                audio_path.unlink()


def _run_mlx_whisper(
    python_executable: str,
    audio_path: Path,
    transcript_path: Path,
    model: str,
    language: str,
    prompt: str,
) -> None:
    command = [
        python_executable,
        str(PROJECT_ROOT / "backend/services/mlx_whisper_runner.py"),
        "--audio",
        str(audio_path),
        "--output",
        str(transcript_path),
        "--model",
        model,
        "--language",
        language or "auto",
    ]
    if prompt:
        command.extend(["--prompt", prompt])
    result = subprocess.run(command, cwd=audio_path.parent, capture_output=True, check=False)
    if result.returncode == 0 and transcript_path.is_file():
        return
    detail = decode_process_output(result.stderr or result.stdout).strip()
    if len(detail) > 3000:
        detail = detail[-3000:]
    raise RuntimeError(f"MLX Whisper 转录失败：{detail or '没有生成转录文件'}")
