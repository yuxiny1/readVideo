import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.downloader import clean_filename_part, download_video, normalize_downloaded_file_path


class FakeYoutubeDLWithRequestedDownload:
    def __init__(self, options):
        self.options = options

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
        ):
            downloaded = Path(download_video("https://youtu.be/demo", tmpdir, progress_events.append))

            self.assertEqual(downloaded.name, "Demo Video.mp4")
            self.assertTrue(downloaded.exists())
            self.assertEqual(progress_events[0]["status"], "finished")


if __name__ == "__main__":
    unittest.main()
