import openai
import os
from moviepy.editor import AudioFileClip
import wave

class AudioTranscription:
    def __init__(self, api_key: str, model: str = "whisper-1"):
        self.api_key = api_key
        self.model = model
        openai.api_key = self.api_key  # Initialize the API key once

    def split_audio_by_duration(self, audio_path: str, chunk_duration_sec: int) -> list:
        """
        Split the audio file into chunks based on duration (in seconds).
        """
        chunks = []
        try:
            with wave.open(audio_path, 'rb') as wave_file:
                framerate = wave_file.getframerate()
                num_frames = wave_file.getnframes()
                frames_per_chunk = framerate * chunk_duration_sec
                audio_data = wave_file.readframes(num_frames)
                
                for i in range(0, len(audio_data), frames_per_chunk * 2):
                    chunk_data = audio_data[i:i + frames_per_chunk * 2]
                    chunk_file_path = f"{audio_path}_chunk_{i // (frames_per_chunk * 2)}.wav"
                    with wave.open(chunk_file_path, 'wb') as chunk:
                        chunk.setnchannels(1)
                        chunk.setsampwidth(2)  # 16-bit audio
                        chunk.setframerate(framerate)
                        chunk.writeframes(chunk_data)
                    chunks.append(chunk_file_path)
        except Exception as e:
            print(f"Error splitting audio: {e}")
        return chunks

    def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Transcribe audio using OpenAI Whisper or another API model.
        """
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcription = openai.Audio.transcribe(model=self.model, file=audio_file)
                return transcription['text']
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return ""

    def save_transcription(self, text: str, original_video_path: str):
        """
        Save the transcribed text to a dynamically named file based on the original video file.
        """
        try:
            base_name = os.path.splitext(os.path.basename(original_video_path))[0]
            output_file_path = f"{base_name}_transcription.txt"
            with open(output_file_path, "w") as text_file:
                text_file.write(text)
            print(f"Transcription saved to {output_file_path}")
        except Exception as e:
            print(f"Error saving transcription: {e}")

    def delete_chunk_files(self, chunks: list):
        """
        Delete chunk files after transcription is successful.
        """
        for chunk_path in chunks:
            try:
                os.remove(chunk_path)
                print(f"Deleted chunk: {chunk_path}")
            except Exception as e:
                print(f"Error deleting chunk {chunk_path}: {e}")

    def process_audio_file(self, audio_file_path: str, chunk_duration_sec: int = 180):
        """
        Process the audio file: split into chunks, transcribe, and clean up.
        """
        # Step 1: Split the audio into chunks
        audio_chunks = self.split_audio_by_duration(audio_file_path, chunk_duration_sec)
        
        # Step 2: Transcribe each chunk and accumulate the results
        full_transcription = ""
        for chunk_path in audio_chunks:
            transcription_text = self.transcribe_audio(chunk_path)
            if transcription_text:
                full_transcription += transcription_text + "\n\n"
            # Step 3: Delete chunk files after transcription
            self.delete_chunk_files([chunk_path])

        # Step 4: Save the transcription to a file
        self.save_transcription(full_transcription, audio_file_path)
        
        return full_transcription  # Optionally return the full transcription
