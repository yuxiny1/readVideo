import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.media_audio import extract_audio


class MediaAudioTest(unittest.TestCase):
    def test_extract_audio_requires_ffmpeg(self):
        with patch("backend.services.media_audio.shutil.which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "未找到 ffmpeg"):
                extract_audio("video.mp4", "audio.wav")

    def test_extract_audio_runs_mono_16khz_conversion(self):
        with (
            patch("backend.services.media_audio.shutil.which", return_value="/usr/bin/ffmpeg"),
            patch("backend.services.media_audio.run_command") as run_command,
        ):
            extract_audio("video.mp4", "audio.wav")

        command = run_command.call_args.args[0]
        self.assertEqual(command[0], "ffmpeg")
        self.assertIn("-ac", command)
        self.assertIn("1", command)
        self.assertIn("-ar", command)
        self.assertIn("16000", command)
        self.assertEqual(command[-1], str(Path("audio.wav")))


if __name__ == "__main__":
    unittest.main()
