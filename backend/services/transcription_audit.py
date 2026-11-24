import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


AUDIT_SCHEMA_VERSION = 1


def audit_path_for_transcript(transcript_path: str | Path) -> Path:
    path = Path(transcript_path)
    return path.with_suffix(".audit.json")


def write_transcription_audit(
    transcript_path: str | Path,
    *,
    backend: str,
    model: str,
    chunk_seconds: int,
    audio_duration_ms: int,
    chunks: Iterable[dict[str, Any]],
    output_path: str | Path | None = None,
) -> Path:
    path = Path(transcript_path)
    chunk_records = [dict(chunk) for chunk in chunks]
    processed_duration_ms = sum(int(chunk["duration_ms"]) for chunk in chunk_records)
    complete = (
        audio_duration_ms > 0
        and processed_duration_ms == audio_duration_ms
        and _windows_are_contiguous(chunk_records, audio_duration_ms)
    )
    if not complete:
        raise RuntimeError(
            "转录完整性检查失败：分段没有从音频开头连续覆盖到结尾，拒绝保存完成状态。"
        )

    payload = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "backend": backend,
        "model": model,
        "complete": True,
        "audio_duration_ms": audio_duration_ms,
        "processed_duration_ms": processed_duration_ms,
        "coverage_percent": 100.0,
        "chunk_seconds": chunk_seconds,
        "expected_chunks": len(chunk_records),
        "completed_chunks": len(chunk_records),
        "transcript_sha256": _sha256(path),
        "chunks": chunk_records,
    }
    audit_path = Path(output_path) if output_path is not None else audit_path_for_transcript(path)
    temporary_path = audit_path.with_suffix(f"{audit_path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary_path.replace(audit_path)
    return audit_path


def read_valid_transcription_audit(transcript_path: str | Path) -> dict[str, Any] | None:
    path = Path(transcript_path)
    audit_path = audit_path_for_transcript(path)
    if not path.is_file() or not audit_path.is_file():
        return None
    try:
        payload = json.loads(audit_path.read_text(encoding="utf-8"))
        chunks = payload["chunks"]
        audio_duration_ms = int(payload["audio_duration_ms"])
        processed_duration_ms = int(payload["processed_duration_ms"])
        expected_chunks = int(payload["expected_chunks"])
        completed_chunks = int(payload["completed_chunks"])
        coverage_percent = float(payload.get("coverage_percent", 0))
        transcript_sha256 = _sha256(path)
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None

    valid = (
        payload.get("schema_version") == AUDIT_SCHEMA_VERSION
        and payload.get("complete") is True
        and audio_duration_ms > 0
        and processed_duration_ms == audio_duration_ms
        and coverage_percent == 100.0
        and isinstance(chunks, list)
        and expected_chunks == completed_chunks == len(chunks)
        and _windows_are_contiguous(chunks, audio_duration_ms)
        and payload.get("transcript_sha256") == transcript_sha256
    )
    return payload if valid else None


def transcription_audit_is_valid(transcript_path: str | Path) -> bool:
    return read_valid_transcription_audit(transcript_path) is not None


def _windows_are_contiguous(chunks: list[dict[str, Any]], audio_duration_ms: int) -> bool:
    if not chunks:
        return False
    expected_offset = 0
    try:
        for index, chunk in enumerate(chunks, start=1):
            if int(chunk["index"]) != index:
                return False
            offset_ms = int(chunk["offset_ms"])
            duration_ms = int(chunk["duration_ms"])
            if offset_ms != expected_offset or duration_ms <= 0:
                return False
            expected_offset += duration_ms
    except (ValueError, TypeError, KeyError):
        return False
    return expected_offset == audio_duration_ms


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
