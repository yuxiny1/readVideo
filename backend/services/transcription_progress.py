from backend.core.task_state import append_task_log, update_task_details
from backend.services.local_transcription import TranscriptionProgress


def transcription_progress_hook(task_id: str):
    def report(progress: TranscriptionProgress) -> None:
        update_task_details(
            task_id,
            transcription_chunks_completed=progress.completed_chunks,
            transcription_chunks_total=progress.total_chunks,
            transcription_percent=progress.percent,
            transcription_coverage_percent=progress.percent,
        )
        if progress.completed_chunks:
            append_task_log(
                task_id,
                (
                    f"转录进度：第 {progress.completed_chunks}/{progress.total_chunks} 段完成，"
                    f"已验证覆盖 {progress.percent:.1f}% 音频。"
                ),
                status="transcribing",
            )

    return report


def transcription_result_details(result) -> dict:
    details = {
        "chunk_count": getattr(result, "chunk_count", None),
        "transcription_audit_path": getattr(result, "audit_path", ""),
        "transcription_audio_duration_ms": getattr(result, "audio_duration_ms", 0),
        "transcription_processed_duration_ms": getattr(result, "processed_duration_ms", 0),
        "transcription_coverage_percent": getattr(result, "coverage_percent", 0.0),
        "transcription_chunk_character_counts": list(
            getattr(result, "chunk_character_counts", ())
        ),
    }
    return {
        key: value
        for key, value in details.items()
        if value is not None and value != ""
    }
