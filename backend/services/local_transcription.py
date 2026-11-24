import json
import re
import shutil
import subprocess
import wave
from dataclasses import dataclass
from functools import lru_cache
from math import ceil
from pathlib import Path
from typing import Callable

from backend.services.downloader import clean_filename_part
from backend.services.media_audio import (
    CommandExecutionError,
    DEFAULT_AUDIO_FILTER,
    build_ffmpeg_command as _build_ffmpeg_command,
    run_command as _run_command,
)
from backend.services.transcription_audit import (
    audit_path_for_transcript,
    write_transcription_audit,
)


@dataclass(frozen=True)
class LocalTranscriptionResult:
    text: str
    transcription_path: str
    model_path: str
    recovered_encoding: bool = False
    decode_error: str = ""
    chunk_count: int = 1
    audio_duration_ms: int = 0
    processed_duration_ms: int = 0
    coverage_percent: float = 0.0
    audit_path: str = ""
    chunk_character_counts: tuple[int, ...] = ()


@dataclass(frozen=True)
class TranscriptionProgress:
    completed_chunks: int
    total_chunks: int
    processed_duration_ms: int
    audio_duration_ms: int

    @property
    def percent(self) -> float:
        if self.audio_duration_ms <= 0:
            return 0.0
        return round(min(100.0, self.processed_duration_ms * 100 / self.audio_duration_ms), 1)


@dataclass(frozen=True)
class WhisperTimestampMetadata:
    segment_count: int = 0
    last_segment_ms: int = 0
    boundary_overrun_ms: int = 0


@dataclass(frozen=True)
class TranscriptTextResult:
    text: str
    recovered_encoding: bool = False
    decode_error: str = ""


class LocalWhisperTranscription:
    def __init__(
        self,
        whisper_cli: str = "whisper-cli",
        model_path: str = "models/ggml-large-v3.bin",
        language: str = "auto",
        prompt: str = "",
        audio_filter: str = DEFAULT_AUDIO_FILTER,
        chunk_seconds: int = 300,
        progress_callback: Callable[[TranscriptionProgress], None] | None = None,
    ):
        self.whisper_cli = whisper_cli
        self.model_path = model_path
        self.language = language or "auto"
        self.prompt = prompt
        self.audio_filter = audio_filter
        self.chunk_seconds = chunk_seconds
        self.progress_callback = progress_callback

    def _validate(self):
        if shutil.which("ffmpeg") is None:
            raise RuntimeError("未找到 ffmpeg，请运行以下命令安装：brew install ffmpeg")

        if shutil.which(self.whisper_cli) is None:
            raise RuntimeError(
                f"未找到 {self.whisper_cli}，请运行以下命令安装：brew install whisper-cpp"
            )

        if not Path(self.model_path).is_file():
            raise RuntimeError(
                f"未在 {self.model_path} 找到本地 Whisper 模型。"
                "请从 https://huggingface.co/ggerganov/whisper.cpp/tree/main 下载模型。"
            )
        if self.chunk_seconds <= 0:
            raise RuntimeError("whisper.cpp 音频分段时长必须大于 0。")

    def process_video(self, video_file_path: str) -> LocalTranscriptionResult:
        self._validate()

        video_path = Path(video_file_path)
        if not video_path.is_file():
            raise FileNotFoundError(f"找不到视频文件：{video_file_path}")

        audio_path = video_path.with_suffix(".local-whisper.wav")
        output_base = video_path.with_name(f"{clean_filename_part(video_path.stem)}_transcription")
        transcript_path = output_base.with_suffix(".txt")
        part_paths: list[Path] = []
        temporary_transcript_path = transcript_path.with_suffix(f"{transcript_path.suffix}.tmp")
        audit_path = audit_path_for_transcript(transcript_path)
        temporary_audit_path = audit_path.with_suffix(f"{audit_path.suffix}.pending")
        checkpoint_path = output_base.with_suffix(".checkpoint.json")
        completed_successfully = False

        try:
            _run_command(_build_ffmpeg_command(video_path, audio_path, self.audio_filter))
            audio_duration_ms = _audio_duration_ms(audio_path)
            supported_flags = _supported_whisper_flags(self.whisper_cli)
            windows = _transcription_windows(
                audio_path,
                self.chunk_seconds,
                supported_flags,
            )
            effective_windows = [
                (
                    offset_ms if offset_ms is not None else 0,
                    duration_ms if duration_ms is not None else audio_duration_ms,
                )
                for offset_ms, duration_ms in windows
            ]
            checkpoint_identity = _checkpoint_identity(
                video_path=video_path,
                audio_duration_ms=audio_duration_ms,
                windows=effective_windows,
                whisper_cli=self.whisper_cli,
                model_path=self.model_path,
                language=self.language,
                prompt=self.prompt,
                audio_filter=self.audio_filter,
                chunk_seconds=self.chunk_seconds,
            )
            completed_chunks = _load_checkpoint(checkpoint_path, checkpoint_identity)
            if completed_chunks is None:
                _remove_stale_part_files(output_base)
                completed_chunks = set()
                _write_checkpoint(checkpoint_path, checkpoint_identity, completed_chunks)
            transcript_parts: list[str] = []
            recovered_encoding = False
            decode_errors: list[str] = []
            chunk_records: list[dict[str, int | float]] = []
            processed_duration_ms = 0
            self._report_progress(0, len(windows), 0, audio_duration_ms)
            for index, (offset_ms, duration_ms) in enumerate(windows, start=1):
                part_base = Path(f"{output_base}.part-{index:03d}")
                part_path = Path(f"{part_base}.txt")
                part_json_path = Path(f"{part_base}.json")
                part_paths.extend((part_path, part_json_path))
                effective_offset_ms, effective_duration_ms = effective_windows[index - 1]
                transcript = None
                timestamp_metadata = WhisperTimestampMetadata()
                if index in completed_chunks:
                    try:
                        transcript = read_transcript_text(part_path)
                        normalized_checkpoint = _normalize_whisper_text(transcript.text).strip()
                        if _preferred_flag(supported_flags, "-oj", "--output-json"):
                            timestamp_metadata = _read_whisper_timestamp_metadata(
                                part_json_path,
                                effective_offset_ms,
                                effective_duration_ms,
                                require_segments=bool(normalized_checkpoint),
                            )
                    except (OSError, RuntimeError):
                        transcript = None
                        completed_chunks.discard(index)

                if transcript is None:
                    for generated_path in (part_path, part_json_path):
                        generated_path.unlink(missing_ok=True)
                    command = _build_whisper_command(
                        self.whisper_cli,
                        self.model_path,
                        audio_path,
                        self.language,
                        part_base,
                        self.prompt,
                        supported_flags,
                        offset_ms=offset_ms,
                        duration_ms=duration_ms,
                    )
                    _run_whisper_with_retry(command, supported_flags)
                    if not part_path.is_file():
                        raise FileNotFoundError(
                            f"whisper.cpp 完成了第 {index}/{len(windows)} 段，"
                            f"但没有生成转录文件：{part_path}"
                        )
                    transcript = read_transcript_text(part_path)

                recovered_encoding = recovered_encoding or transcript.recovered_encoding
                if transcript.decode_error:
                    decode_errors.append(transcript.decode_error)
                normalized_part = _normalize_whisper_text(transcript.text).strip()
                if normalized_part:
                    transcript_parts.append(normalized_part)

                if (
                    timestamp_metadata.segment_count == 0
                    and _preferred_flag(supported_flags, "-oj", "--output-json")
                ):
                    timestamp_metadata = _read_whisper_timestamp_metadata(
                        part_json_path,
                        effective_offset_ms,
                        effective_duration_ms,
                        require_segments=bool(normalized_part),
                    )
                if index not in completed_chunks:
                    completed_chunks.add(index)
                    _write_checkpoint(checkpoint_path, checkpoint_identity, completed_chunks)
                character_count = len(re.sub(r"\s+", "", normalized_part))
                processed_duration_ms += effective_duration_ms
                chunk_records.append(
                    {
                        "index": index,
                        "offset_ms": effective_offset_ms,
                        "duration_ms": effective_duration_ms,
                        "characters": character_count,
                        "segment_count": timestamp_metadata.segment_count,
                        "last_segment_ms": timestamp_metadata.last_segment_ms,
                        "boundary_overrun_ms": timestamp_metadata.boundary_overrun_ms,
                        "timestamp_coverage_percent": round(
                            min(100.0, timestamp_metadata.last_segment_ms * 100 / effective_duration_ms),
                            1,
                        ) if effective_duration_ms else 0.0,
                    }
                )
                self._report_progress(
                    index,
                    len(windows),
                    processed_duration_ms,
                    audio_duration_ms,
                )

            text = _normalize_whisper_text("\n".join(transcript_parts))
            temporary_transcript_path.write_text(text, encoding="utf-8")
            write_transcription_audit(
                temporary_transcript_path,
                backend="whisper.cpp",
                model=self.model_path,
                chunk_seconds=self.chunk_seconds,
                audio_duration_ms=audio_duration_ms,
                chunks=chunk_records,
                output_path=temporary_audit_path,
            )
            temporary_transcript_path.replace(transcript_path)
            temporary_audit_path.replace(audit_path)
            completed_successfully = True
            return LocalTranscriptionResult(
                text=text,
                transcription_path=str(transcript_path),
                model_path=self.model_path,
                recovered_encoding=recovered_encoding,
                decode_error="; ".join(decode_errors),
                chunk_count=len(windows),
                audio_duration_ms=audio_duration_ms,
                processed_duration_ms=processed_duration_ms,
                coverage_percent=round(processed_duration_ms * 100 / audio_duration_ms, 1),
                audit_path=str(audit_path),
                chunk_character_counts=tuple(
                    int(chunk["characters"])
                    for chunk in chunk_records
                ),
            )
        finally:
            temporary_transcript_path.unlink(missing_ok=True)
            temporary_audit_path.unlink(missing_ok=True)
            if completed_successfully:
                for part_path in part_paths:
                    part_path.unlink(missing_ok=True)
                checkpoint_path.unlink(missing_ok=True)
            if audio_path.exists():
                audio_path.unlink()

    def _report_progress(
        self,
        completed_chunks: int,
        total_chunks: int,
        processed_duration_ms: int,
        audio_duration_ms: int,
    ) -> None:
        if self.progress_callback is None:
            return
        self.progress_callback(
            TranscriptionProgress(
                completed_chunks=completed_chunks,
                total_chunks=total_chunks,
                processed_duration_ms=processed_duration_ms,
                audio_duration_ms=audio_duration_ms,
            )
        )


def read_transcript_text(transcript_path: str | Path) -> TranscriptTextResult:
    path = Path(transcript_path)
    try:
        return TranscriptTextResult(text=path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as exc:
        text = path.read_bytes().decode("utf-8", errors="replace")
        return TranscriptTextResult(text=text, recovered_encoding=True, decode_error=str(exc))


def _normalize_whisper_text(text: str) -> str:
    lines = []
    previous_line = ""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"\s+", " ", line)
        if line == previous_line:
            continue
        lines.append(line)
        previous_line = line
    return "\n".join(lines) + ("\n" if lines else "")


def _resolve_transcript_path(
    expected_path: Path,
    output_base: Path,
    audio_path: Path,
    video_path: Path,
) -> Path:
    candidates = [
        expected_path,
        output_base.with_suffix(".txt"),
        audio_path.with_suffix(".txt"),
        video_path.with_suffix(".txt"),
        video_path.with_name(f"{video_path.stem}.txt"),
        video_path.with_name(f"{clean_filename_part(video_path.stem)}.txt"),
    ]
    for candidate in candidates:
        if candidate.is_file():
            return _standardize_transcript_path(candidate, expected_path)

    recent_txt_files = sorted(
        expected_path.parent.glob("*.txt"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for candidate in recent_txt_files[:8]:
        if _looks_like_whisper_output(candidate, video_path, output_base):
            return _standardize_transcript_path(candidate, expected_path)

    checked = "\n".join(str(candidate) for candidate in dict.fromkeys(candidates))
    raise FileNotFoundError(f"Whisper 已完成，但没有找到转录文件。已检查：\n{checked}")


def _standardize_transcript_path(found_path: Path, expected_path: Path) -> Path:
    if found_path == expected_path:
        return expected_path
    if expected_path.exists():
        expected_path.unlink()
    found_path.replace(expected_path)
    return expected_path


def _looks_like_whisper_output(candidate: Path, video_path: Path, output_base: Path) -> bool:
    candidate_stem = clean_filename_part(candidate.stem).lower()
    video_stem = clean_filename_part(video_path.stem).lower()
    output_stem = clean_filename_part(output_base.stem).lower()
    audio_stem = f"{video_stem}.local-whisper"
    return (
        candidate_stem in {video_stem, output_stem, audio_stem}
        or candidate_stem.startswith(video_stem[:80])
        or output_stem.startswith(candidate_stem)
    )


def _build_whisper_command(
    whisper_cli: str,
    model_path: str,
    audio_path: Path,
    language: str,
    output_base: Path,
    prompt: str = "",
    supported_flags: set[str] | None = None,
    disable_flash_attention: bool = False,
    offset_ms: int | None = None,
    duration_ms: int | None = None,
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
    json_flag = _preferred_flag(flags, "-oj", "--output-json")
    if json_flag:
        command.append(json_flag)
    if prompt and "--prompt" in flags:
        command.extend(["--prompt", prompt])
    if "-sns" in flags or "--suppress-nst" in flags:
        command.append("-sns")
    if "-sow" in flags or "--split-on-word" in flags:
        command.append("-sow")
    if "-ml" in flags or "--max-len" in flags:
        command.extend(["-ml", "96"])
    offset_flag = _preferred_flag(flags, "-ot", "--offset-t")
    duration_flag = _preferred_flag(flags, "-d", "--duration")
    flash_attention_flag = _preferred_flag(flags, "-nfa", "--no-flash-attn")
    if offset_ms is not None and offset_flag:
        command.extend([offset_flag, str(offset_ms)])
    if duration_ms is not None and duration_flag:
        command.extend([duration_flag, str(duration_ms)])
    if disable_flash_attention and flash_attention_flag:
        command.append(flash_attention_flag)
    return command


def _run_whisper_with_retry(command: list[str], supported_flags: set[str]) -> None:
    try:
        _run_command(command)
    except CommandExecutionError as exc:
        if not _should_retry_without_flash_attention(exc, supported_flags):
            raise
        flash_attention_flag = _preferred_flag(
            supported_flags,
            "-nfa",
            "--no-flash-attn",
        )
        retry_command = [*command, flash_attention_flag]
        try:
            _run_command(retry_command)
        except CommandExecutionError as retry_exc:
            raise RuntimeError(
                "whisper.cpp 的 Metal 转录失败，关闭 Flash Attention 重试后仍未成功。\n"
                f"{retry_exc}"
            ) from retry_exc


def _preferred_flag(flags: set[str], short_flag: str, long_flag: str) -> str:
    if short_flag in flags:
        return short_flag
    if long_flag in flags:
        return long_flag
    return ""


def _transcription_windows(
    audio_path: Path,
    chunk_seconds: int,
    supported_flags: set[str],
) -> list[tuple[int | None, int | None]]:
    total_ms = _audio_duration_ms(audio_path)
    supports_windows = (
        ("-ot" in supported_flags or "--offset-t" in supported_flags)
        and ("-d" in supported_flags or "--duration" in supported_flags)
    )
    if not supports_windows:
        if total_ms > chunk_seconds * 1000:
            raise RuntimeError(
                "当前 whisper.cpp 不支持按时间窗口转录长音频（缺少 offset/duration 参数）。"
                "请运行 brew upgrade whisper-cpp 后重试。"
            )
        return [(None, None)]

    chunk_ms = chunk_seconds * 1000
    windows = [
        (offset_ms, min(chunk_ms, total_ms - offset_ms))
        for offset_ms in range(0, total_ms, chunk_ms)
    ]
    if len(windows) > 1 and windows[-1][1] < 1000:
        previous_offset, _ = windows[-2]
        windows[-2] = (previous_offset, total_ms - previous_offset)
        windows.pop()
    return windows or [(0, total_ms)]


def _audio_duration_ms(audio_path: Path) -> int:
    with wave.open(str(audio_path), "rb") as audio:
        frame_rate = audio.getframerate()
        if frame_rate <= 0:
            raise RuntimeError(f"无法读取音频采样率：{audio_path}")
        total_ms = ceil(audio.getnframes() * 1000 / frame_rate)
    if total_ms <= 0:
        raise RuntimeError(f"音频没有可处理的内容：{audio_path}")
    return total_ms


def _checkpoint_identity(
    *,
    video_path: Path,
    audio_duration_ms: int,
    windows: list[tuple[int, int]],
    whisper_cli: str,
    model_path: str,
    language: str,
    prompt: str,
    audio_filter: str,
    chunk_seconds: int,
) -> dict:
    source_stat = video_path.stat()
    model = Path(model_path)
    model_stat = model.stat() if model.is_file() else None
    return {
        "source_path": str(video_path.resolve()),
        "source_size": source_stat.st_size,
        "source_mtime_ns": source_stat.st_mtime_ns,
        "audio_duration_ms": audio_duration_ms,
        "windows": [[offset, duration] for offset, duration in windows],
        "whisper_cli": whisper_cli,
        "model_path": str(model.expanduser().resolve()),
        "model_size": model_stat.st_size if model_stat else 0,
        "model_mtime_ns": model_stat.st_mtime_ns if model_stat else 0,
        "language": language,
        "prompt": prompt,
        "audio_filter": audio_filter,
        "chunk_seconds": chunk_seconds,
    }


def _load_checkpoint(checkpoint_path: Path, identity: dict) -> set[int] | None:
    if not checkpoint_path.is_file():
        return None
    try:
        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if payload.get("identity") != identity:
            return None
        return {int(index) for index in payload.get("completed_chunks", [])}
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _write_checkpoint(checkpoint_path: Path, identity: dict, completed_chunks: set[int]) -> None:
    temporary_path = checkpoint_path.with_suffix(f"{checkpoint_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(
            {
                "identity": identity,
                "completed_chunks": sorted(completed_chunks),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    temporary_path.replace(checkpoint_path)


def _remove_stale_part_files(output_base: Path) -> None:
    for path in output_base.parent.glob(f"{output_base.name}.part-*"):
        if path.suffix in {".txt", ".json"}:
            path.unlink(missing_ok=True)


def _read_whisper_timestamp_metadata(
    json_path: Path,
    offset_ms: int,
    duration_ms: int,
    *,
    require_segments: bool,
) -> WhisperTimestampMetadata:
    if not json_path.is_file():
        raise FileNotFoundError(f"whisper.cpp 没有生成时间戳审计文件：{json_path}")
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        segments = payload["transcription"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取 whisper.cpp 时间戳审计文件：{json_path}") from exc
    if not isinstance(segments, list):
        raise RuntimeError(f"whisper.cpp 时间戳审计格式无效：{json_path}")
    if require_segments and not segments:
        raise RuntimeError(f"whisper.cpp 生成了文本但没有对应时间戳：{json_path}")

    first_from_ms: int | None = None
    previous_to_ms = 0
    for segment in segments:
        try:
            offsets = segment["offsets"]
            from_ms = int(offsets["from"])
            to_ms = int(offsets["to"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"whisper.cpp 时间戳片段格式无效：{json_path}") from exc
        if from_ms < previous_to_ms or to_ms < from_ms:
            raise RuntimeError(f"whisper.cpp 时间戳顺序无效：{json_path}")
        if first_from_ms is None:
            first_from_ms = from_ms
        previous_to_ms = to_ms

    uses_absolute_timestamps = bool(
        offset_ms
        and first_from_ms is not None
        and first_from_ms >= offset_ms - 30_000
    )
    relative_last_ms = previous_to_ms - offset_ms if uses_absolute_timestamps else previous_to_ms
    boundary_overrun_ms = max(0, relative_last_ms - duration_ms)
    last_segment_ms = min(duration_ms, max(0, relative_last_ms))
    return WhisperTimestampMetadata(
        segment_count=len(segments),
        last_segment_ms=last_segment_ms,
        boundary_overrun_ms=boundary_overrun_ms,
    )


def _should_retry_without_flash_attention(
    error: CommandExecutionError,
    supported_flags: set[str],
) -> bool:
    if "-nfa" not in supported_flags and "--no-flash-attn" not in supported_flags:
        return False
    output = error.output.lower()
    metal_started = "ggml_metal_init" in output or "using mtl" in output
    no_actionable_error = not any(
        marker in output
        for marker in ("failed to", "error:", "invalid ", "not found", "cannot open")
    )
    return error.returncode < 0 or (metal_started and no_actionable_error)


@lru_cache(maxsize=4)
def _supported_whisper_flags(whisper_cli: str) -> set[str]:
    try:
        result = subprocess.run([whisper_cli, "--help"], capture_output=True, text=True, check=False)
    except OSError:
        return set()
    help_text = f"{result.stdout}\n{result.stderr}"
    return set(re.findall(r"(?<!\w)(?:--?[A-Za-z][A-Za-z0-9-]*)", help_text))
