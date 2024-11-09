import openai
import os
from moviepy.editor import AudioFileClip
import wave

# Set your OpenAI API key
with open('apiKey.json', 'r') as f:
    config = json.load(f)

api_key = config["apiKey"]

# Path to the video file
video_file_path = "/Users/xinyiyu/Desktop/20241109-比特幣歷史新高！4個我還敢買的理由！【邦妮區塊鏈】.mp4"

# Convert video to audio
audio_file_path = "/Users/xinyiyu/Desktop/new_audio.wav"
audio = AudioFileClip(video_file_path)
audio.write_audiofile(audio_file_path)

# Set the OpenAI API key
openai.api_key = api_key

# Function to split audio into chunks based on duration (seconds)
def split_audio_by_duration(audio_path, chunk_duration_sec):
    with wave.open(audio_path, 'rb') as wave_file:
        # Get the frame rate and number of frames in the audio
        framerate = wave_file.getframerate()
        num_frames = wave_file.getnframes()
        
        # Calculate the number of frames per chunk
        frames_per_chunk = framerate * chunk_duration_sec
        
        # Read audio data
        audio_data = wave_file.readframes(num_frames)
        
        # Create chunks
        chunks = []
        for i in range(0, len(audio_data), frames_per_chunk * 2):  # Each frame is 2 bytes (16-bit audio)
            chunk_data = audio_data[i:i + frames_per_chunk * 2]
            chunk_file_path = f"/Users/xinyiyu/Desktop/chunk_{i // (frames_per_chunk * 2)}.wav"
            chunk = wave.open(chunk_file_path, 'wb')
            chunk.setnchannels(1)  # Mono channel
            chunk.setsampwidth(2)  # 16-bit audio
            chunk.setframerate(framerate)
            chunk.writeframes(chunk_data)
            chunk.close()
            chunks.append(chunk_file_path)
    
    return chunks

# Split audio into 180-second chunks (3 minutes per chunk)
chunk_duration_sec = 180
audio_chunks = split_audio_by_duration(audio_file_path, chunk_duration_sec)

# Function to transcribe audio using OpenAI Whisper model
def transcribe_audio_with_openai(audio_file_path):
    try:
        with open(audio_file_path, "rb") as audio_file:
            transcription = openai.Audio.transcribe(
                file=audio_file,
                model="whisper-1",
            )
        return transcription['text']
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return ""

# Function to delete chunk files after successful transcription
def delete_chunk_files(chunks):
    for chunk_path in chunks:
        try:
            os.remove(chunk_path)  # Delete the chunk file after transcription
            print(f"Deleted chunk: {chunk_path}")
        except Exception as e:
            print(f"Error deleting chunk {chunk_path}: {e}")

# Transcribe each chunk and save the transcriptions
output_file_path = "/Users/xinyiyu/Desktop/20241109_transcriptions.txt"
with open(output_file_path, "w") as output_file:
    for chunk_path in audio_chunks:
        transcription_text = transcribe_audio_with_openai(chunk_path)
        
        if transcription_text:
            output_file.write(transcription_text + "\n\n")
            # Only delete the chunk after successful transcription
            delete_chunk_files([chunk_path])

print(f"Transcription saved to {output_file_path}")