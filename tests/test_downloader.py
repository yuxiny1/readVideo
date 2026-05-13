import unittest
from pathlib import Path

from backend.services.downloader import _build_ydl_options


class DownloaderTest(unittest.TestCase):
    def test_audio_options_prefer_audio_only_without_video_merge(self):
        options = _build_ydl_options(Path("downloads"), "audio")

        self.assertEqual(options["format"], "bestaudio[ext=m4a]/bestaudio/best")
        self.assertNotIn("merge_output_format", options)
        self.assertTrue(options["noplaylist"])

    def test_video_options_keep_full_video_mode_available(self):
        options = _build_ydl_options(Path("downloads"), "video")

        self.assertEqual(options["format"], "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best")
        self.assertEqual(options["merge_output_format"], "mp4")

    def test_options_reject_unknown_media_type(self):
        with self.assertRaisesRegex(ValueError, "audio or video"):
            _build_ydl_options(Path("downloads"), "images")
