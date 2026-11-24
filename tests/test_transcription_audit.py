import json
import tempfile
import unittest
from pathlib import Path

from backend.services.transcription_audit import (
    audit_path_for_transcript,
    read_valid_transcription_audit,
    transcription_audit_is_valid,
    write_transcription_audit,
)


class TranscriptionAuditTest(unittest.TestCase):
    def test_write_and_validate_complete_audit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "video_transcription.txt"
            transcript.write_text("完整转录\n", encoding="utf-8")

            audit_path = write_transcription_audit(
                transcript,
                backend="whisper.cpp",
                model="large-v3",
                chunk_seconds=300,
                audio_duration_ms=650_000,
                chunks=[
                    {"index": 1, "offset_ms": 0, "duration_ms": 300_000},
                    {"index": 2, "offset_ms": 300_000, "duration_ms": 300_000},
                    {"index": 3, "offset_ms": 600_000, "duration_ms": 50_000},
                ],
            )
            payload = read_valid_transcription_audit(transcript)

        self.assertEqual(audit_path.name, "video_transcription.audit.json")
        self.assertEqual(payload["coverage_percent"], 100.0)
        self.assertEqual(payload["completed_chunks"], 3)

    def test_modified_transcript_invalidates_audit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "video_transcription.txt"
            transcript.write_text("original\n", encoding="utf-8")
            write_transcription_audit(
                transcript,
                backend="whisper.cpp",
                model="large-v3",
                chunk_seconds=300,
                audio_duration_ms=1000,
                chunks=[{"index": 1, "offset_ms": 0, "duration_ms": 1000}],
            )

            transcript.write_text("truncated\n", encoding="utf-8")

            self.assertFalse(transcription_audit_is_valid(transcript))

    def test_incomplete_windows_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "video_transcription.txt"
            transcript.write_text("text\n", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "没有从音频开头连续覆盖到结尾"):
                write_transcription_audit(
                    transcript,
                    backend="whisper.cpp",
                    model="large-v3",
                    chunk_seconds=300,
                    audio_duration_ms=2000,
                    chunks=[{"index": 1, "offset_ms": 0, "duration_ms": 1000}],
                )

    def test_malformed_audit_is_not_trusted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "video_transcription.txt"
            transcript.write_text("text\n", encoding="utf-8")
            audit_path_for_transcript(transcript).write_text(
                json.dumps({"complete": True}),
                encoding="utf-8",
            )

            self.assertIsNone(read_valid_transcription_audit(transcript))


if __name__ == "__main__":
    unittest.main()
