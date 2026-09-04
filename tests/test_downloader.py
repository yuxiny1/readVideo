import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.downloader import (
    DOWNLOAD_RETRIES,
    HTTP_CHUNK_SIZE,
    YtDlpLogger,
    _retry_delay,
    clean_filename_part,
    download_video,
    normalize_downloaded_file_path,
)


class FakeYoutubeDLWithRequestedDownload:
    last_options = None

    def __init__(self, options):
        self.options = options
        type(self).last_options = options

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def extract_info(self, url, download=False):
        output_dir = Path(self.options["outtmpl"]).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        downloaded = output_dir / "  Demo   Video .MP4"
        downloaded.write_text("video", encoding="utf-8")
        for hook in self.options["progress_hooks"]:
            hook({"status": "finished", "filename": str(downloaded)})
        return {"requested_downloads": [{"filepath": str(downloaded)}]}


class DownloaderFilenameTest(unittest.TestCase):
    def test_clean_filename_part_trims_and_collapses_spacing(self):
        cleaned = clean_filename_part("  计算机科学与技术——入门课40讲全   p01   1  ")

        self.assertEqual(cleaned, "计算机科学与技术——入门课40讲全 p01 1")

    def test_normalize_downloaded_file_path_renames_dirty_filename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dirty_path = Path(tmpdir) / "  lesson   01  .MP4"
            dirty_path.write_text("video", encoding="utf-8")

            normalized = Path(normalize_downloaded_file_path(str(dirty_path)))

            self.assertEqual(normalized.name, "lesson 01.mp4")
            self.assertTrue(normalized.exists())
            self.assertFalse(dirty_path.exists())

    def test_download_video_uses_yt_dlp_metadata_path_and_normalizes_name(self):
        progress_events = []
        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "backend.services.downloader.yt_dlp.YoutubeDL",
            FakeYoutubeDLWithRequestedDownload,
        ), patch(
            "backend.services.downloader.shutil.which",
            return_value="/opt/homebrew/bin/node",
        ):
            downloaded = Path(download_video("https://youtu.be/demo", tmpdir, progress_events.append))

            self.assertEqual(downloaded.name, "Demo Video.mp4")
            self.assertTrue(downloaded.exists())
            self.assertEqual(progress_events[0]["status"], "finished")
            self.assertEqual(
                FakeYoutubeDLWithRequestedDownload.last_options["logger"].name,
                "backend.services.downloader",
            )
            self.assertEqual(FakeYoutubeDLWithRequestedDownload.last_options["retries"], DOWNLOAD_RETRIES)
            self.assertEqual(FakeYoutubeDLWithRequestedDownload.last_options["fragment_retries"], DOWNLOAD_RETRIES)
            self.assertEqual(FakeYoutubeDLWithRequestedDownload.last_options["http_chunk_size"], HTTP_CHUNK_SIZE)
            self.assertTrue(FakeYoutubeDLWithRequestedDownload.last_options["continuedl"])
            self.assertFalse(FakeYoutubeDLWithRequestedDownload.last_options["nopart"])
            self.assertEqual(
                FakeYoutubeDLWithRequestedDownload.last_options["js_runtimes"],
                {"node": {"path": "/opt/homebrew/bin/node"}},
            )
            self.assertEqual(
                FakeYoutubeDLWithRequestedDownload.last_options["color"],
                {"stdout": "never", "stderr": "never"},
            )

    def test_yt_dlp_logger_reports_retry_attempts_to_the_task_hook(self):
        progress_events = []
        task_logger = YtDlpLogger(progress_events.append)

        task_logger.debug("[download] Got error: Connection closed. Retrying (2/20)...")

        self.assertEqual(progress_events, [{
            "status": "retrying",
            "retry_attempt": 2,
            "retry_limit": 20,
        }])

    def test_retry_delay_accepts_yt_dlp_keyword_argument(self):
        self.assertEqual(_retry_delay(n=0), 1)
        self.assertEqual(_retry_delay(n=3), 8)
        self.assertEqual(_retry_delay(n=8), 10)

    def test_download_does_not_create_a_log_file_in_the_process_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "backend.services.downloader.yt_dlp.YoutubeDL",
            FakeYoutubeDLWithRequestedDownload,
        ), patch(
            "backend.services.downloader.logging.basicConfig",
            side_effect=PermissionError("只读应用目录"),
        ) as configure_file_logging:
            downloaded = download_video("https://youtu.be/demo", tmpdir)
            self.assertTrue(Path(downloaded).is_file())

        configure_file_logging.assert_not_called()


if __name__ == "__main__":
    unittest.main()
