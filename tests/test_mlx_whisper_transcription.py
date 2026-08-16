import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from backend.services.mlx_whisper_runner import transcript_text
from backend.services.mlx_whisper_transcription import MlxWhisperTranscription, _run_mlx_whisper


class MlxWhisperTranscriptionTest(unittest.TestCase):
    def test_segment_text_removes_adjacent_repetitions_without_dropping_later_content(self):
        result = transcript_text({"segments": [
            {"text": " 计算机科学很重要。"},
            {"text": "计算机科学很重要。"},
            {"text": "接下来介绍巴贝奇。"},
            {"text": "计算机科学很重要。"},
        ]})

        self.assertEqual(
            result,
            "计算机科学很重要。\n接下来介绍巴贝奇。\n计算机科学很重要。\n",
        )

    def test_process_video_extracts_audio_and_writes_utf8_transcript(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            video = Path(tmpdir) / "课程.mp4"
            video.write_bytes(b"video")

            def fake_transcribe(**kwargs):
                kwargs["transcript_path"].write_text("第一段\n第二段\n", encoding="utf-8")

            service = MlxWhisperTranscription("~/mlx-env/bin/python", "mlx/model", language="zh")
            with patch.object(service, "_validated_python", return_value="/mlx/python"), patch(
                "backend.services.mlx_whisper_transcription.run_command"
            ) as run, patch(
                "backend.services.mlx_whisper_transcription._run_mlx_whisper",
                side_effect=fake_transcribe,
            ):
                result = service.process_video(str(video))

        self.assertEqual(result.text, "第一段\n第二段\n")
        self.assertEqual(result.model_path, "mlx/model")
        run.assert_called_once()

    def test_subprocess_error_is_decoded_for_the_task_log(self):
        failed = CompletedProcess(args=[], returncode=1, stdout=b"", stderr=b"bad \xe4\xff")
        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "backend.services.mlx_whisper_transcription.subprocess.run", return_value=failed
        ):
            with self.assertRaisesRegex(RuntimeError, "MLX Whisper 转录失败：bad"):
                _run_mlx_whisper(
                    "/mlx/python",
                    Path(tmpdir) / "audio.wav",
                    Path(tmpdir) / "transcript.txt",
                    "mlx/model",
                    "auto",
                    "",
                )


if __name__ == "__main__":
    unittest.main()
