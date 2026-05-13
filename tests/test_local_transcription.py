import unittest
import tempfile
from pathlib import Path
import wave

from backend.services.local_transcription import (
    _build_ffmpeg_command,
    _build_whisper_command,
    _normalize_whisper_text,
    _split_wav_by_duration,
)


class LocalTranscriptionTest(unittest.TestCase):
    def test_normalize_whisper_text_strips_empty_lines(self):
        text = _normalize_whisper_text(" first line  \n\nsecond   line\n")

        self.assertEqual(text, "first line\nsecond line\n")

    def test_normalize_whisper_text_removes_repeated_latin_hallucination(self):
        text = _normalize_whisper_text(
            "有效內容\nennachronom\nennachronom\nennachronomal\n下一段內容\n"
        )

        self.assertEqual(text, "有效內容\n下一段內容\n")

    def test_split_wav_by_duration_preserves_params(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "sample.wav"
            with wave.open(str(audio_path), "wb") as wav:
                wav.setnchannels(1)
                wav.setsampwidth(2)
                wav.setframerate(10)
                wav.writeframes(b"\0" * 2 * 25)

            chunks = _split_wav_by_duration(audio_path, chunk_seconds=1)

            self.assertEqual(len(chunks), 3)
            with wave.open(str(chunks[0]), "rb") as first_chunk:
                self.assertEqual(first_chunk.getnchannels(), 1)
                self.assertEqual(first_chunk.getsampwidth(), 2)
                self.assertEqual(first_chunk.getframerate(), 10)

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
