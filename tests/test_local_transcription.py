import unittest
from pathlib import Path

from backend.services.local_transcription import (
    _build_ffmpeg_command,
    _build_whisper_command,
    _normalize_whisper_text,
)


class LocalTranscriptionTest(unittest.TestCase):
    def test_normalize_whisper_text_strips_empty_lines(self):
        text = _normalize_whisper_text(" first line  \n\nsecond   line\n")

        self.assertEqual(text, "first line\nsecond line\n")

    def test_build_ffmpeg_command_applies_speech_filter(self):
        command = _build_ffmpeg_command(
            Path("video.mp4"),
            Path("audio.wav"),
            "highpass=f=80,lowpass=f=8000",
        )

        self.assertIn("-af", command)
        self.assertIn("highpass=f=80,lowpass=f=8000", command)
        self.assertIn("16000", command)
        self.assertEqual(command[-1], "audio.wav")

    def test_build_whisper_command_defaults_to_auto_and_quality_flags(self):
        command = _build_whisper_command(
            "whisper-cli",
            "models/ggml-small.bin",
            Path("audio.wav"),
            "auto",
            Path("out"),
            "Jim Keller, CUDA",
            {"-nt", "--prompt", "-sns"},
        )

        self.assertIn("auto", command)
        self.assertIn("-nt", command)
        self.assertIn("-sns", command)
        self.assertIn("--prompt", command)
        self.assertIn("Jim Keller, CUDA", command)

    def test_build_whisper_command_skips_unsupported_optional_flags(self):
        command = _build_whisper_command(
            "whisper-cli",
            "models/ggml-small.bin",
            Path("audio.wav"),
            "",
            Path("out"),
            "ignored",
            set(),
        )

        self.assertIn("auto", command)
        self.assertNotIn("-nt", command)
        self.assertNotIn("-sns", command)
        self.assertNotIn("--prompt", command)


if __name__ == "__main__":
    unittest.main()
