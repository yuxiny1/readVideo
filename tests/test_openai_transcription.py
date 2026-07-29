import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from backend.services.openai_transcription import AudioTranscription


class FakeTranscription:
    text = "hello from fake openai"


class FakeTranscriptions:
    def create(self, model, file):
        return FakeTranscription()


class FakeAudio:
    transcriptions = FakeTranscriptions()


class FakeClient:
    audio = FakeAudio()


class CapturingTranscriptions:
    payload = None

    def create(self, **payload):
        self.payload = payload
        return FakeTranscription()


class CapturingAudio:
    def __init__(self):
        self.transcriptions = CapturingTranscriptions()


class CapturingClient:
    def __init__(self):
        self.audio = CapturingAudio()


class DictTranscriptions:
    def create(self, model, file):
        return {"text": "hello from dict response"}


class DictAudio:
    transcriptions = DictTranscriptions()


class DictClient:
    audio = DictAudio()


class AudioTranscriptionTest(unittest.TestCase):
    def test_split_audio_by_duration_preserves_wave_params(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = f"{tmpdir}/sample.wav"
            with wave.open(audio_path, "wb") as wav:
                wav.setnchannels(2)
                wav.setsampwidth(2)
                wav.setframerate(10)
                wav.writeframes(b"\0" * 2 * 2 * 25)

            service = AudioTranscription(client=FakeClient())
            chunks = service.split_audio_by_duration(audio_path, chunk_duration_sec=1)

            self.assertEqual(len(chunks), 3)
            with wave.open(chunks[0], "rb") as first_chunk:
                self.assertEqual(first_chunk.getnchannels(), 2)
                self.assertEqual(first_chunk.getsampwidth(), 2)
                self.assertEqual(first_chunk.getframerate(), 10)

            service.delete_chunk_files(chunks)

    def test_transcribe_audio_reads_text_attribute(self):
        with tempfile.NamedTemporaryFile(suffix=".wav") as audio_file:
            service = AudioTranscription(client=FakeClient())
            self.assertEqual(service.transcribe_audio(audio_file.name), "hello from fake openai")

    def test_transcribe_audio_reads_dict_response(self):
        with tempfile.NamedTemporaryFile(suffix=".wav") as audio_file:
            service = AudioTranscription(client=DictClient())
            self.assertEqual(service.transcribe_audio(audio_file.name), "hello from dict response")

    def test_transcribe_audio_sends_language_and_prompt_when_configured(self):
        client = CapturingClient()
        with tempfile.NamedTemporaryFile(suffix=".wav") as audio_file:
            service = AudioTranscription(
                model="gpt-4o-transcribe",
                language="en",
                prompt="Jim Keller, CUDA",
                client=client,
            )
            service.transcribe_audio(audio_file.name)

        self.assertEqual(client.audio.transcriptions.payload["model"], "gpt-4o-transcribe")
        self.assertEqual(client.audio.transcriptions.payload["language"], "en")
        self.assertEqual(client.audio.transcriptions.payload["prompt"], "Jim Keller, CUDA")

    def test_process_video_requires_existing_file(self):
        service = AudioTranscription(client=FakeClient())
        with self.assertRaises(FileNotFoundError):
            service.process_video("/tmp/readvideo-missing-file.mp4")

    def test_process_video_extracts_audio_with_ffmpeg(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "sample.mp4"
            chunk_path = Path(tmpdir) / "sample_chunk_0.wav"
            video_path.write_bytes(b"video")
            chunk_path.write_bytes(b"audio")
            service = AudioTranscription(client=FakeClient())

            with (
                patch("backend.services.openai_transcription.extract_audio") as extract,
                patch.object(
                    service,
                    "split_audio_by_duration",
                    return_value=[str(chunk_path)],
                ),
            ):
                result = service.process_video(str(video_path))

            extract.assert_called_once_with(video_path, video_path.with_suffix(".wav"))
            self.assertEqual(result.text, "hello from fake openai")
            self.assertEqual(result.chunk_count, 1)


if __name__ == "__main__":
    unittest.main()
