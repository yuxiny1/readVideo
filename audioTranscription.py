import openai
import os
from moviepy.editor import AudioFileClip
import wave
import json

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
            # Ensure the directory for chunk files exists
            output_dir = os.path.dirname(audio_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # Get file base name for chunk naming
            base_name = os.path.splitext(os.path.basename(audio_path))[0]

            with wave.open(audio_path, 'rb') as wave_file:
                framerate = wave_file.getframerate()
                num_frames = wave_file.getnframes()
                frames_per_chunk = framerate * chunk_duration_sec
                audio_data = wave_file.readframes(num_frames)

                for i in range(0, len(audio_data), frames_per_chunk * 2):
                    chunk_data = audio_data[i:i + frames_per_chunk * 2]
                    
                    # Create a unique file name for each chunk
                    chunk_file_path = os.path.join(output_dir, f"{base_name}_chunk_{i // (frames_per_chunk * 2)}.wav")
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
            # Extract the base name of the video file (without extension)
            base_name = os.path.splitext(os.path.basename(original_video_path))[0]
            
            # Create the output file path for the transcription (same name as video, but with _transcription.txt suffix)
            output_file_path = os.path.join(os.path.dirname(original_video_path), f"{base_name}_transcription.txt")
            
            # Save the transcription text to the file
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

    def process_video(self, video_file_path: str, chunk_duration_sec: int = 180):
        """
        Process the video: convert it to audio, split it into chunks, transcribe, and clean up.
        """
        
        # Step 1: Convert video to audio
        audio_file_path = video_file_path.replace(".mp4", ".wav")  # Change to appropriate audio file format
        audio = AudioFileClip(video_file_path)
        audio.write_audiofile(audio_file_path)

        # Step 2: Split the audio into chunks
        audio_chunks = self.split_audio_by_duration(audio_file_path, chunk_duration_sec)
        
        # Step 3: Transcribe each chunk and accumulate the results
        full_transcription = ""
        for chunk_path in audio_chunks:
            transcription_text = self.transcribe_audio(chunk_path)
            if transcription_text:
                full_transcription += transcription_text + "\n\n"
            # Step 4: Delete chunk files after transcription
            self.delete_chunk_files([chunk_path])

        # Step 5: Save the transcription to a file
        self.save_transcription(full_transcription, video_file_path)
        
        return full_transcription  # Optionally return the full transcription


# Example Usage:
# Assuming you already have the downloaded video file, call the process method with the correct video file.
# with open('apiKey.json', 'r') as f:
#     config = json.load(f)

# api_key = config["apiKey"]

# audio_transcription = AudioTranscription(api_key=api_key)
# video_file_path = "/path/to/your/video.mp4"
# transcription = audio_transcription.process_video(video_file_path)
# print(transcription)