import tempfile
import unittest
import wave

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

    def test_process_video_requires_existing_file(self):
        service = AudioTranscription(client=FakeClient())
        with self.assertRaises(FileNotFoundError):
            service.process_video("/tmp/readvideo-missing-file.mp4")


if __name__ == "__main__":
    unittest.main()
