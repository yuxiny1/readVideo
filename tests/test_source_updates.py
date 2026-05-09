import unittest
from unittest.mock import patch

from backend.services.source_updates import list_source_updates


class FakeYoutubeDL:
    def __init__(self, options):
        self.options = options

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def extract_info(self, url, download=False):
        return {
            "channel": "Demo Channel",
            "entries": [
                {
                    "id": "abc123",
                    "title": "Latest video",
                    "url": "abc123",
                    "upload_date": "20260509",
                    "duration": 120,
                }
            ],
        }


class SourceUpdatesTest(unittest.TestCase):
    def test_list_source_updates_normalizes_flat_entries(self):
        with patch("backend.services.source_updates.yt_dlp.YoutubeDL", FakeYoutubeDL):
            updates = list_source_updates("https://www.youtube.com/@demo", limit=1)

        self.assertEqual(len(updates), 1)
        self.assertEqual(updates[0].title, "Latest video")
        self.assertEqual(updates[0].url, "https://www.youtube.com/watch?v=abc123")
        self.assertEqual(updates[0].uploader, "Demo Channel")


if __name__ == "__main__":
    unittest.main()
