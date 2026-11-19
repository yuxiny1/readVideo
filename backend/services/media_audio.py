import shutil
import signal
import subprocess
from pathlib import Path


DEFAULT_AUDIO_FILTER = "highpass=f=80,lowpass=f=8000,loudnorm=I=-16:TP=-1.5:LRA=11"


class CommandExecutionError(RuntimeError):
    def __init__(self, command: list[str], returncode: int, output: str):
        self.command = command
        self.returncode = returncode
        self.output = output
        super().__init__(_format_command_error(command, returncode, output))


def extract_audio(
    video_path: str | Path,
    audio_path: str | Path,
    audio_filter: str = DEFAULT_AUDIO_FILTER,
) -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("未找到 ffmpeg，请运行以下命令安装：brew install ffmpeg")
    run_command(build_ffmpeg_command(Path(video_path), Path(audio_path), audio_filter))


def build_ffmpeg_command(
    video_path: Path,
    audio_path: Path,
    audio_filter: str = DEFAULT_AUDIO_FILTER,
) -> list[str]:
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


def run_command(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode == 0:
        return

    output = decode_process_output(result.stderr or result.stdout).strip()
    if len(output) > 2000:
        output = output[-2000:]
    raise CommandExecutionError(command, result.returncode, output)


def _format_command_error(command: list[str], returncode: int, output: str) -> str:
    if returncode < 0:
        signal_number = -returncode
        try:
            signal_name = signal.Signals(signal_number).name
        except ValueError:
            signal_name = "UNKNOWN"
        exit_detail = f"系统信号 {signal_name} ({signal_number})"
    else:
        exit_detail = f"退出码 {returncode}"
    detail = f"命令执行失败（{exit_detail}）：{' '.join(command[:2])}"
    return f"{detail}\n{output}" if output else detail


def decode_process_output(output: object) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return str(output)
