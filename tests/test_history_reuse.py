import tempfile
import unittest
from pathlib import Path

from backend.services.history_reuse import find_history_reuse_candidate
from backend.services.transcription_audit import write_transcription_audit
from backend.storage.history import HistoryStore


class HistoryReuseTest(unittest.TestCase):
    def test_local_transcript_requires_a_valid_audit_before_reuse(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            database_path = str(Path(tmpdir) / "history.sqlite3")
            video = Path(tmpdir) / "video.mp4"
            transcript = Path(tmpdir) / "video_transcription.txt"
            video.write_text("video", encoding="utf-8")
            transcript.write_text("transcript", encoding="utf-8")
            HistoryStore(database_path).upsert_task(
                {
                    "task_id": "local-task",
                    "status": "completed",
                    "url": "https://youtu.be/audit123",
                    "video_path": str(video),
                    "transcription_path": str(transcript),
                    "transcription_backend": "local",
                    "created_at": "2026-11-21T00:00:00",
                    "updated_at": "2026-11-21T00:01:00",
                }
            )

            candidate = find_history_reuse_candidate(
                database_path,
                "https://youtu.be/audit123",
                tmpdir,
            )
            self.assertFalse(candidate.transcript_verified)
            self.assertFalse(candidate.can_reuse_transcript)

            write_transcription_audit(
                transcript,
                backend="whisper.cpp",
                model="large-v3",
                chunk_seconds=300,
                audio_duration_ms=1000,
                chunks=[{"index": 1, "offset_ms": 0, "duration_ms": 1000}],
            )
            verified = find_history_reuse_candidate(
                database_path,
                "https://youtu.be/audit123",
                tmpdir,
            )
            transcript_verified = verified.transcript_verified
            can_reuse_transcript = verified.can_reuse_transcript

        self.assertTrue(transcript_verified)
        self.assertTrue(can_reuse_transcript)


if __name__ == "__main__":
    unittest.main()
