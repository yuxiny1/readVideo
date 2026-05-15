import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.core.task_state import TASKS, clear_tasks
from backend.services.markdown_notes import NoteResult
from backend.services.video_processor import process_video
from backend.storage.history import HistoryStore


class VideoProcessorReuseTest(unittest.TestCase):
    def setUp(self):
        clear_tasks()

    def test_process_video_reuses_downloaded_video_and_transcript(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "history.sqlite3")
            video = Path(tmpdir) / "video.mp4"
            transcript = Path(tmpdir) / "video_transcription.txt"
            note = Path(tmpdir) / "video.md"
            video.write_text("video", encoding="utf-8")
            transcript.write_text("existing transcript", encoding="utf-8")
            HistoryStore(db_path).upsert_task(
                {
                    "task_id": "old-task",
                    "status": "completed",
                    "url": "https://www.youtube.com/watch?v=abc123",
                    "title": "Existing Video",
                    "video_path": str(video),
                    "transcription_path": str(transcript),
                    "markdown_path": str(note),
                    "summary": "- old",
                    "created_at": "2026-05-09T10:00:00",
                    "updated_at": "2026-05-09T10:02:00",
                    "completed_at": "2026-05-09T10:02:00",
                }
            )

            with patch.dict(
                "os.environ",
                {
                    "READVIDEO_DATABASE_PATH": db_path,
                    "READVIDEO_DOWNLOAD_DIR": tmpdir,
                    "READVIDEO_TRANSCRIPTION_BACKEND": "local",
                },
                clear=True,
            ), patch(
                "backend.services.video_processor.download_video",
                side_effect=AssertionError("download should not run"),
            ), patch(
                "backend.services.video_processor.transcribe_video",
                side_effect=AssertionError("transcription should not run"),
            ), patch(
                "backend.services.video_processor.write_markdown_note",
                return_value=NoteResult(
                    markdown_path=str(note),
                    summary="- regenerated",
                    section_count=1,
                    summary_backend="extractive",
                ),
            ) as write_note:
                asyncio.run(process_video("new-task", "https://youtu.be/abc123"))

        task = TASKS["new-task"]
        self.assertEqual(task["status"], "completed")
        self.assertEqual(task["download_status"], "reused")
        self.assertEqual(task["reused_from_task_id"], "old-task")
        self.assertEqual(task["transcription_backend"], "reused")
        write_note.assert_called_once()
        self.assertEqual(write_note.call_args.args[0], "existing transcript")


if __name__ == "__main__":
    unittest.main()
