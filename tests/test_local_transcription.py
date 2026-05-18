import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from backend.services.local_transcription import (
    LocalWhisperTranscription,
    _build_ffmpeg_command,
    _build_whisper_command,
    _normalize_whisper_text,
    _run_command,
    _resolve_transcript_path,
    _supported_whisper_flags,
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

    def test_supported_whisper_flags_parses_help_output_and_handles_missing_cli(self):
        _supported_whisper_flags.cache_clear()
        result = CompletedProcess(
            args=["whisper-cli", "--help"],
            returncode=0,
            stdout="usage: whisper-cli -nt --prompt -sns",
            stderr="also supports --max-len",
        )
        with patch("backend.services.local_transcription.subprocess.run", return_value=result):
            flags = _supported_whisper_flags("whisper-cli")

        self.assertIn("-nt", flags)
        self.assertIn("--prompt", flags)
        self.assertIn("--max-len", flags)

        _supported_whisper_flags.cache_clear()
        with patch("backend.services.local_transcription.subprocess.run", side_effect=OSError):
            self.assertEqual(_supported_whisper_flags("missing-whisper"), set())

    def test_run_command_raises_with_trimmed_error_output(self):
        long_error = "x" * 2105
        result = CompletedProcess(args=["ffmpeg"], returncode=1, stdout="", stderr=long_error)
        with patch("backend.services.local_transcription.subprocess.run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "Command failed: ffmpeg"):
                _run_command(["ffmpeg", "-version"])

    def test_validate_reports_missing_dependencies_and_model(self):
        service = LocalWhisperTranscription(whisper_cli="whisper-cli", model_path="missing.bin")
        with patch("backend.services.local_transcription.shutil.which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "ffmpeg was not found"):
                service._validate()

        def fake_which(command):
            return "/usr/bin/ffmpeg" if command == "ffmpeg" else None

        with patch("backend.services.local_transcription.shutil.which", side_effect=fake_which):
            with self.assertRaisesRegex(RuntimeError, "whisper-cli was not found"):
                service._validate()

        with patch("backend.services.local_transcription.shutil.which", return_value="/usr/local/bin/tool"):
            with self.assertRaisesRegex(RuntimeError, "Local Whisper model not found"):
                service._validate()


if __name__ == "__main__":
    unittest.main()
