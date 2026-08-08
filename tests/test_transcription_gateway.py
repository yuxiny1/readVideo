import unittest
from unittest.mock import patch

from backend.core.config import Settings
from backend.services.transcription_gateway import transcribe_video


class TranscriptionGatewayTest(unittest.TestCase):
    @patch("backend.services.transcription_gateway.LocalWhisperTranscription")
    def test_local_transcription_configuration_stays_inside_gateway(self, transcriber_type):
        transcriber_type.return_value.process_video.return_value = "local-result"
        settings = Settings(
            transcription_backend="local",
            local_whisper_cli="whisper-cli-custom",
            local_whisper_model="models/large.bin",
            local_whisper_language="zh",
            local_whisper_prompt="domain words",
            local_whisper_audio_filter="loudnorm",
        )

        result = transcribe_video("video.mp4", settings)

        self.assertEqual(result, "local-result")
        transcriber_type.assert_called_once_with(
            whisper_cli="whisper-cli-custom",
            model_path="models/large.bin",
            language="zh",
            prompt="domain words",
            audio_filter="loudnorm",
        )
        transcriber_type.return_value.process_video.assert_called_once_with("video.mp4")

    @patch("backend.services.transcription_gateway.AudioTranscription")
    def test_openai_chunking_configuration_stays_inside_gateway(self, transcriber_type):
        transcriber_type.return_value.process_video.return_value = "openai-result"
        settings = Settings(
            transcription_backend="openai",
            openai_api_key="secret",
            transcription_model="transcriber",
            local_whisper_language="en",
            local_whisper_prompt="names",
            chunk_seconds=240,
        )

        result = transcribe_video("video.mp4", settings)

        self.assertEqual(result, "openai-result")
        transcriber_type.assert_called_once_with(
            api_key="secret",
            model="transcriber",
            language="en",
            prompt="names",
        )
        transcriber_type.return_value.process_video.assert_called_once_with("video.mp4", 240)


if __name__ == "__main__":
    unittest.main()
