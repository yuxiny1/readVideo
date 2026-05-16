import tempfile
import unittest
from pathlib import Path

from backend.services.downloader import clean_filename_part, normalize_downloaded_file_path


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


if __name__ == "__main__":
    unittest.main()
