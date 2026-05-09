import unittest

from backend.services.local_transcription import _normalize_whisper_text


class LocalTranscriptionTest(unittest.TestCase):
    def test_normalize_whisper_text_strips_empty_lines(self):
        text = _normalize_whisper_text(" first line  \n\nsecond   line\n")

        self.assertEqual(text, "first line\nsecond line\n")


if __name__ == "__main__":
    unittest.main()
