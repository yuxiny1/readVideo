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
    _should_retry_without_flash_attention,
    _resolve_transcript_path,
    _supported_whisper_flags,
    read_transcript_text,
)
from backend.services.media_audio import CommandExecutionError


class LocalTranscriptionTest(unittest.TestCase):
    def test_normalize_whisper_text_strips_empty_lines(self):
        text = _normalize_whisper_text(" first line  \n\nsecond   line\n")

        self.assertEqual(text, "first line\nsecond line\n")

    def test_normalize_whisper_text_deduplicates_adjacent_repeats(self):
        text = _normalize_whisper_text("repeat\n repeat \nnext\nrepeat\n")

        self.assertEqual(text, "repeat\nnext\nrepeat\n")

    def test_read_transcript_text_recovers_invalid_utf8_bytes(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            transcript = Path(tmpdir) / "video_transcription.txt"
            transcript.write_bytes("hello 中文 ".encode("utf-8") + b"\xe4\xff" + " still readable".encode("utf-8"))

            result = read_transcript_text(transcript)

        self.assertTrue(result.recovered_encoding)
        self.assertIn("hello 中文", result.text)
        self.assertIn("still readable", result.text)
        self.assertIn("\ufffd", result.text)
        self.assertIn("invalid", result.decode_error)

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

    def test_build_whisper_command_can_disable_flash_attention_for_retry(self):
        command = _build_whisper_command(
            "whisper-cli",
            "models/ggml-large-v3.bin",
            Path("audio.wav"),
            "zh",
            Path("out"),
            supported_flags={"-nfa"},
            disable_flash_attention=True,
        )

        self.assertIn("-nfa", command)

    def test_metal_failure_without_actionable_error_uses_safe_retry(self):
        error = CommandExecutionError(
            ["whisper-cli", "-m"],
            1,
            "ggml_metal_init: allocating\nwhisper_full_with_state: auto-detected language: zh",
        )

        self.assertTrue(_should_retry_without_flash_attention(error, {"-nfa"}))

    def test_invalid_model_error_does_not_retry(self):
        error = CommandExecutionError(
            ["whisper-cli", "-m"],
            1,
            "ggml_metal_init: allocating\nerror: failed to load model",
        )

        self.assertFalse(_should_retry_without_flash_attention(error, {"-nfa"}))

    def test_process_video_retries_metal_failure_without_flash_attention(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "sample.mp4"
            video_path.write_bytes(b"video")
            calls = []

            def run(command):
                calls.append(command)
                if command[0] == "ffmpeg":
                    Path(command[-1]).write_bytes(b"wav")
                elif len(calls) == 2:
                    raise CommandExecutionError(
                        command,
                        1,
                        "ggml_metal_init: allocating\n"
                        "whisper_full_with_state: auto-detected language: zh",
                    )
                else:
                    Path(tmpdir, "sample_transcription.txt").write_text(
                        "转录成功\n",
                        encoding="utf-8",
                    )

            service = LocalWhisperTranscription(model_path="model.bin")
            with (
                patch.object(service, "_validate"),
                patch("backend.services.local_transcription._run_command", side_effect=run),
                patch(
                    "backend.services.local_transcription._supported_whisper_flags",
                    return_value={"-nfa"},
                ),
            ):
                result = service.process_video(str(video_path))

        self.assertEqual(result.text, "转录成功\n")
        self.assertEqual(len(calls), 3)
        self.assertNotIn("-nfa", calls[1])
        self.assertIn("-nfa", calls[2])

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
        with patch("backend.services.media_audio.subprocess.run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "命令执行失败（退出码 1）：ffmpeg"):
                _run_command(["ffmpeg", "-version"])

    def test_run_command_decodes_invalid_process_output_for_errors(self):
        result = CompletedProcess(args=["whisper-cli"], returncode=1, stdout=b"", stderr=b"bad output \xe4\xff")
        with patch("backend.services.media_audio.subprocess.run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, "bad output"):
                _run_command(["whisper-cli", "-m"])

    def test_run_command_reports_termination_signal(self):
        result = CompletedProcess(args=["whisper-cli"], returncode=-9, stdout=b"", stderr=b"")
        with patch("backend.services.media_audio.subprocess.run", return_value=result):
            with self.assertRaisesRegex(RuntimeError, r"SIGKILL \(9\)"):
                _run_command(["whisper-cli", "-m"])

    def test_validate_reports_missing_dependencies_and_model(self):
        service = LocalWhisperTranscription(whisper_cli="whisper-cli", model_path="missing.bin")
        with patch("backend.services.local_transcription.shutil.which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "未找到 ffmpeg"):
                service._validate()

        def fake_which(command):
            return "/usr/bin/ffmpeg" if command == "ffmpeg" else None

        with patch("backend.services.local_transcription.shutil.which", side_effect=fake_which):
            with self.assertRaisesRegex(RuntimeError, "未找到 whisper-cli"):
                service._validate()

        with patch("backend.services.local_transcription.shutil.which", return_value="/usr/local/bin/tool"):
            with self.assertRaisesRegex(RuntimeError, "未在 missing.bin 找到本地 Whisper 模型"):
                service._validate()


if __name__ == "__main__":
    unittest.main()
