import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from backend.core.task_state import TASKS, clear_tasks, set_task_status
from backend.services.markdown_notes import NoteResult
from backend.services.video_processor import (
    _download_percent,
    build_download_progress_hook,
    delete_downloaded_video_after_completion,
    process_video,
)
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
                asyncio.run(process_video("new-task", "https://youtu.be/abc123", note_style="commercial"))

        task = TASKS["new-task"]
        self.assertEqual(task["status"], "completed")
        self.assertEqual(task["download_status"], "reused")
        self.assertEqual(task["note_style"], "commercial")
        self.assertEqual(task["reused_from_task_id"], "old-task")
        self.assertEqual(task["transcription_backend"], "reused")
        write_note.assert_called_once()
        self.assertEqual(write_note.call_args.kwargs["transcript_text"], "existing transcript")

    def test_process_video_recovers_invalid_utf8_reused_transcript(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "history.sqlite3")
            video = Path(tmpdir) / "video.mp4"
            transcript = Path(tmpdir) / "video_transcription.txt"
            note = Path(tmpdir) / "video.md"
            video.write_text("video", encoding="utf-8")
            transcript.write_bytes("existing ".encode("utf-8") + b"\xe4\xff" + " transcript".encode("utf-8"))
            HistoryStore(db_path).upsert_task(
                {
                    "task_id": "old-task",
                    "status": "completed",
                    "url": "https://www.youtube.com/watch?v=badutf8",
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
                asyncio.run(process_video("new-task", "https://youtu.be/badutf8"))
                rewritten_transcript = transcript.read_text(encoding="utf-8")

        task = TASKS["new-task"]
        self.assertEqual(task["status"], "completed")
        self.assertIn("\ufffd", write_note.call_args.kwargs["transcript_text"])
        self.assertTrue(any("invalid UTF-8 bytes" in log["message"] for log in task["logs"]))
        self.assertEqual(rewritten_transcript, write_note.call_args.kwargs["transcript_text"])

    def test_process_video_deletes_local_video_after_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = str(Path(tmpdir) / "history.sqlite3")
            video = Path(tmpdir) / "downloaded.mp4"
            transcript = Path(tmpdir) / "downloaded_transcription.txt"
            note = Path(tmpdir) / "downloaded.md"
            video.write_text("video", encoding="utf-8")
            transcript.write_text("fresh transcript", encoding="utf-8")

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
                return_value=str(video),
            ), patch(
                "backend.services.video_processor.transcribe_video",
                return_value=SimpleNamespace(
                    text="fresh transcript",
                    transcription_path=str(transcript),
                    chunk_count=1,
                ),
            ), patch(
                "backend.services.video_processor.write_markdown_note",
                return_value=NoteResult(
                    markdown_path=str(note),
                    summary="- cleaned",
                    section_count=1,
                    summary_backend="extractive",
                ),
            ):
                asyncio.run(
                    process_video(
                        "cleanup-task",
                        "https://youtu.be/cleanup123",
                        delete_video_after_completion=True,
                    )
                )

            task = TASKS["cleanup-task"]
            record = HistoryStore(db_path).get_record("cleanup-task")

            self.assertFalse(video.exists())
            self.assertEqual(task["status"], "completed")
            self.assertTrue(task["video_deleted_after_completion"])
            self.assertEqual(task["download_status"], "deleted_after_completion")
            self.assertEqual(record.video_path, str(video))
            self.assertTrue(any("Deleted local video after completion" in log["message"] for log in task["logs"]))

    def test_delete_downloaded_video_records_missing_file_without_failing(self):
        set_task_status("missing-delete", "completed")

        deleted = delete_downloaded_video_after_completion("missing-delete", "missing.mp4", "downloads")

        self.assertFalse(deleted)
        self.assertFalse(TASKS["missing-delete"]["video_deleted_after_completion"])
        self.assertIn("already missing", TASKS["missing-delete"]["video_delete_error"])

    def test_download_progress_hook_updates_task_details_and_logs_buckets(self):
        set_task_status("progress-task", "downloading")
        hook = build_download_progress_hook("progress-task")

        with patch("backend.services.video_processor.time.monotonic", side_effect=[1.0, 2.0, 3.0]):
            hook(
                {
                    "status": "downloading",
                    "filename": "/tmp/demo.part",
                    "downloaded_bytes": 50,
                    "total_bytes": 100,
                    "speed": 1024,
                    "eta": 5,
                }
            )
            hook(
                {
                    "status": "downloading",
                    "filename": "/tmp/demo.part",
                    "downloaded_bytes": 75,
                    "total_bytes": 100,
                }
            )
            hook({"status": "finished", "filename": "/tmp/demo.mp4", "downloaded_bytes": 100, "total_bytes": 100})

        task = TASKS["progress-task"]
        self.assertEqual(task["download_status"], "finished")
        self.assertEqual(task["download_filename"], "demo.mp4")
        self.assertEqual(task["download_percent"], 100)
        self.assertTrue(any("Download 50.0% complete." in log["message"] for log in task["logs"]))
        self.assertTrue(any("Download finished" in log["message"] for log in task["logs"]))

    def test_download_percent_handles_missing_and_caps_at_one_hundred(self):
        self.assertIsNone(_download_percent(None, 100))
        self.assertIsNone(_download_percent(100, 0))
        self.assertEqual(_download_percent(150, 100), 100.0)
        self.assertEqual(_download_percent(25, 100), 25.0)


if __name__ == "__main__":
    unittest.main()
