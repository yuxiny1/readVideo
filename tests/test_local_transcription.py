import unittest
import wave
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from backend.services.local_transcription import (
    LocalWhisperTranscription,
    _build_ffmpeg_command,
    _build_whisper_command,
    _normalize_whisper_text,
    _read_whisper_timestamp_metadata,
    _run_command,
    _should_retry_without_flash_attention,
    _transcription_windows,
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

    def test_build_whisper_command_keeps_fallback_context_and_adds_window(self):
        command = _build_whisper_command(
            "whisper-cli",
            "models/ggml-small.bin",
            Path("audio.wav"),
            "auto",
            Path("out"),
            "Jim Keller, CUDA",
            {"-nt", "--prompt", "-sns", "-nf", "-mc", "-sow", "-ml", "-ot", "-d"},
            offset_ms=900_000,
            duration_ms=120_000,
        )

        self.assertIn("auto", command)
        self.assertIn("-sns", command)
        self.assertIn("-sow", command)
        self.assertIn("-ml", command)
        self.assertIn("96", command)
        self.assertNotIn("-nt", command)
        self.assertNotIn("-nf", command)
        self.assertNotIn("-mc", command)
        self.assertEqual(command[command.index("-ot") + 1], "900000")
        self.assertEqual(command[command.index("-d") + 1], "120000")
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

    def test_build_whisper_command_uses_supported_long_window_flags(self):
        command = _build_whisper_command(
            "whisper-cli",
            "models/ggml-large-v3.bin",
            Path("audio.wav"),
            "zh",
            Path("out"),
            supported_flags={"--offset-t", "--duration", "--no-flash-attn"},
            disable_flash_attention=True,
            offset_ms=60_000,
            duration_ms=30_000,
        )

        self.assertEqual(command[command.index("--offset-t") + 1], "60000")
        self.assertEqual(command[command.index("--duration") + 1], "30000")
        self.assertIn("--no-flash-attn", command)

    def test_build_whisper_command_requests_json_timestamps_when_supported(self):
        command = _build_whisper_command(
            "whisper-cli",
            "models/ggml-large-v3.bin",
            Path("audio.wav"),
            "zh",
            Path("out"),
            supported_flags={"-oj"},
        )

        self.assertIn("-oj", command)

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
                    with wave.open(command[-1], "wb") as audio:
                        audio.setparams((1, 2, 10, 0, "NONE", "not compressed"))
                        audio.writeframes(b"\0\0" * 100)
                elif len(calls) == 2:
                    raise CommandExecutionError(
                        command,
                        1,
                        "ggml_metal_init: allocating\n"
                        "whisper_full_with_state: auto-detected language: zh",
                    )
                else:
                    Path(tmpdir, "sample_transcription.part-001.txt").write_text(
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

    def test_transcription_windows_cover_the_complete_audio(self):
        import tempfile
        import wave

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "audio.wav"
            with wave.open(str(audio_path), "wb") as audio:
                audio.setparams((1, 2, 10, 0, "NONE", "not compressed"))
                audio.writeframes(b"\0\0" * 251)

            windows = _transcription_windows(audio_path, 10, {"-ot", "-d"})

        self.assertEqual(windows, [(0, 10_000), (10_000, 10_000), (20_000, 5_100)])

    def test_transcription_windows_merge_a_tiny_codec_padding_tail(self):
        import tempfile
        import wave

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "audio.wav"
            with wave.open(str(audio_path), "wb") as audio:
                audio.setparams((1, 2, 10, 0, "NONE", "not compressed"))
                audio.writeframes(b"\0\0" * 201)

            windows = _transcription_windows(audio_path, 10, {"-ot", "-d"})

        self.assertEqual(windows, [(0, 10_000), (10_000, 10_100)])

    def test_transcription_windows_reject_unsafe_long_audio_on_old_cli(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "audio.wav"
            with wave.open(str(audio_path), "wb") as audio:
                audio.setparams((1, 2, 10, 0, "NONE", "not compressed"))
                audio.writeframes(b"\0\0" * 101)

            with self.assertRaisesRegex(RuntimeError, "不支持按时间窗口转录长音频"):
                _transcription_windows(audio_path, 10, set())

    def test_read_whisper_timestamp_metadata_validates_segments(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "part.json"
            json_path.write_text(
                json.dumps(
                    {
                        "transcription": [
                            {"offsets": {"from": 0, "to": 1200}, "text": "第一句"},
                            {"offsets": {"from": 1200, "to": 3500}, "text": "第二句"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            metadata = _read_whisper_timestamp_metadata(
                json_path,
                offset_ms=0,
                duration_ms=5000,
                require_segments=True,
            )

        self.assertEqual(metadata.segment_count, 2)
        self.assertEqual(metadata.last_segment_ms, 3500)
        self.assertEqual(metadata.boundary_overrun_ms, 0)

    def test_timestamp_metadata_clamps_a_segment_crossing_the_window_boundary(self):
        import json
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "part-006.json"
            json_path.write_text(
                json.dumps(
                    {
                        "transcription": [
                            {
                                "offsets": {"from": 1_500_000, "to": 1_807_420},
                                "text": "跨越窗口边界的一句话",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            metadata = _read_whisper_timestamp_metadata(
                json_path,
                offset_ms=1_500_000,
                duration_ms=300_000,
                require_segments=True,
            )

        self.assertEqual(metadata.last_segment_ms, 300_000)
        self.assertEqual(metadata.boundary_overrun_ms, 7_420)

    def test_process_video_merges_every_transcription_window(self):
        import tempfile
        import wave

        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "long.mp4"
            video_path.write_bytes(b"video")
            whisper_commands = []
            progress = []

            def run(command):
                if command[0] == "ffmpeg":
                    with wave.open(command[-1], "wb") as audio:
                        audio.setparams((1, 2, 10, 0, "NONE", "not compressed"))
                        audio.writeframes(b"\0\0" * 251)
                    return
                whisper_commands.append(command)
                index = len(whisper_commands)
                Path(tmpdir, f"long_transcription.part-{index:03d}.txt").write_text(
                    f"第 {index} 段\n",
                    encoding="utf-8",
                )

            service = LocalWhisperTranscription(
                model_path="model.bin",
                chunk_seconds=10,
                progress_callback=progress.append,
            )
            with (
                patch.object(service, "_validate"),
                patch("backend.services.local_transcription._run_command", side_effect=run),
                patch(
                    "backend.services.local_transcription._supported_whisper_flags",
                    return_value={"-ot", "-d"},
                ),
            ):
                result = service.process_video(str(video_path))

            saved_text = Path(result.transcription_path).read_text(encoding="utf-8")
            audit_exists = Path(result.audit_path).is_file()

        self.assertEqual(result.chunk_count, 3)
        self.assertEqual(result.text, "第 1 段\n第 2 段\n第 3 段\n")
        self.assertEqual(saved_text, result.text)
        self.assertEqual(result.coverage_percent, 100.0)
        self.assertTrue(audit_exists)
        self.assertEqual([item.completed_chunks for item in progress], [0, 1, 2, 3])
        self.assertEqual([cmd[cmd.index("-ot") + 1] for cmd in whisper_commands], ["0", "10000", "20000"])
        self.assertEqual([cmd[cmd.index("-d") + 1] for cmd in whisper_commands], ["10000", "10000", "5100"])

    def test_process_video_keeps_existing_transcript_when_a_window_fails(self):
        import tempfile
        import wave

        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "long.mp4"
            transcript_path = Path(tmpdir) / "long_transcription.txt"
            video_path.write_bytes(b"video")
            transcript_path.write_text("previous complete transcript\n", encoding="utf-8")
            whisper_calls = 0

            def run(command):
                nonlocal whisper_calls
                if command[0] == "ffmpeg":
                    with wave.open(command[-1], "wb") as audio:
                        audio.setparams((1, 2, 10, 0, "NONE", "not compressed"))
                        audio.writeframes(b"\0\0" * 251)
                    return
                whisper_calls += 1
                if whisper_calls == 2:
                    raise CommandExecutionError(command, 1, "window failed")
                Path(tmpdir, f"long_transcription.part-{whisper_calls:03d}.txt").write_text(
                    f"partial {whisper_calls}\n",
                    encoding="utf-8",
                )

            service = LocalWhisperTranscription(model_path="model.bin", chunk_seconds=10)
            with (
                patch.object(service, "_validate"),
                patch("backend.services.local_transcription._run_command", side_effect=run),
                patch(
                    "backend.services.local_transcription._supported_whisper_flags",
                    return_value={"-ot", "-d"},
                ),
            ):
                with self.assertRaises(CommandExecutionError):
                    service.process_video(str(video_path))

            self.assertEqual(
                transcript_path.read_text(encoding="utf-8"),
                "previous complete transcript\n",
            )
            self.assertTrue(Path(tmpdir, "long_transcription.part-001.txt").is_file())
            self.assertTrue(Path(tmpdir, "long_transcription.checkpoint.json").is_file())
            self.assertFalse(Path(tmpdir, "long.local-whisper.wav").exists())

            retry_commands = []

            def retry_run(command):
                if command[0] == "ffmpeg":
                    with wave.open(command[-1], "wb") as audio:
                        audio.setparams((1, 2, 10, 0, "NONE", "not compressed"))
                        audio.writeframes(b"\0\0" * 251)
                    return
                retry_commands.append(command)
                output_base = Path(command[command.index("-of") + 1])
                Path(f"{output_base}.txt").write_text(
                    f"retry {len(retry_commands) + 1}\n",
                    encoding="utf-8",
                )

            with (
                patch.object(service, "_validate"),
                patch("backend.services.local_transcription._run_command", side_effect=retry_run),
                patch(
                    "backend.services.local_transcription._supported_whisper_flags",
                    return_value={"-ot", "-d"},
                ),
            ):
                result = service.process_video(str(video_path))

            self.assertEqual(result.text, "partial 1\nretry 2\nretry 3\n")
            self.assertEqual(
                [command[command.index("-ot") + 1] for command in retry_commands],
                ["10000", "20000"],
            )
            self.assertFalse(list(Path(tmpdir).glob("*.part-*.txt")))
            self.assertFalse(Path(tmpdir, "long_transcription.checkpoint.json").exists())

    def test_process_video_keeps_existing_transcript_when_audit_fails(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "sample.mp4"
            transcript_path = Path(tmpdir) / "sample_transcription.txt"
            video_path.write_bytes(b"video")
            transcript_path.write_text("previous complete transcript\n", encoding="utf-8")

            def run(command):
                if command[0] == "ffmpeg":
                    with wave.open(command[-1], "wb") as audio:
                        audio.setparams((1, 2, 10, 0, "NONE", "not compressed"))
                        audio.writeframes(b"\0\0" * 100)
                    return
                Path(tmpdir, "sample_transcription.part-001.txt").write_text(
                    "new transcript\n",
                    encoding="utf-8",
                )

            service = LocalWhisperTranscription(model_path="model.bin")
            with (
                patch.object(service, "_validate"),
                patch("backend.services.local_transcription._run_command", side_effect=run),
                patch(
                    "backend.services.local_transcription._supported_whisper_flags",
                    return_value={"-ot", "-d"},
                ),
                patch(
                    "backend.services.local_transcription.write_transcription_audit",
                    side_effect=RuntimeError("audit failed"),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "audit failed"):
                    service.process_video(str(video_path))

            self.assertEqual(
                transcript_path.read_text(encoding="utf-8"),
                "previous complete transcript\n",
            )

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
