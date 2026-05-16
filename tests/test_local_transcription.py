import unittest
from pathlib import Path

from backend.services.local_transcription import (
    _build_ffmpeg_command,
    _build_whisper_command,
    _normalize_whisper_text,
    _resolve_transcript_path,
)


class LocalTranscriptionTest(unittest.TestCase):
    def test_normalize_whisper_text_strips_empty_lines(self):
        text = _normalize_whisper_text(" first line  \n\nsecond   line\n")

        self.assertEqual(text, "first line\nsecond line\n")

    def test_normalize_whisper_text_deduplicates_adjacent_repeats(self):
        text = _normalize_whisper_text("repeat\n repeat \nnext\nrepeat\n")

        self.assertEqual(text, "repeat\nnext\nrepeat\n")

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

    def test_resolve_transcript_path_accepts_whisper_default_output_name(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            directory = Path(tmpdir)
            video_path = directory / " 计算机科学与技术——入门课40讲全   p01   1.mp4"
            audio_path = directory / " 计算机科学与技术——入门课40讲全   p01   1.local-whisper.wav"
            output_base = directory / "计算机科学与技术——入门课40讲全 p01 1_transcription"
            expected_path = output_base.with_suffix(".txt")
            whisper_path = video_path.with_suffix(".txt")
            whisper_path.write_text("hello", encoding="utf-8")

            resolved = _resolve_transcript_path(expected_path, output_base, audio_path, video_path)

            self.assertEqual(resolved, expected_path)
            self.assertTrue(expected_path.exists())
            self.assertFalse(whisper_path.exists())

    def test_build_whisper_command_defaults_to_auto_and_quality_flags(self):
        command = _build_whisper_command(
            "whisper-cli",
            "models/ggml-small.bin",
            Path("audio.wav"),
            "auto",
            Path("out"),
            "Jim Keller, CUDA",
            {"-nt", "--prompt", "-sns", "-nf", "-mc", "-sow", "-ml"},
        )

        self.assertIn("auto", command)
        self.assertIn("-nt", command)
        self.assertIn("-sns", command)
        self.assertIn("-nf", command)
        self.assertIn("-sow", command)
        self.assertIn("-mc", command)
        self.assertIn("0", command)
        self.assertIn("-ml", command)
        self.assertIn("96", command)
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
