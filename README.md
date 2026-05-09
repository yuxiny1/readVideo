# readVideo

Download a YouTube video, transcribe its audio, turn the transcript into Markdown notes, and keep a small local watchlist of YouTube channels/playlists.

The default transcription backend is local `whisper.cpp`, so OpenAI API access is optional.

## What It Does

- Downloads a single YouTube video with `yt-dlp`.
- Transcribes speech in the original language; it does not translate between languages.
- Uses local `whisper.cpp` by default, with optional OpenAI transcription support.
- Saves the raw transcript next to the downloaded video.
- Creates a Markdown note with summary, structured sections, and full transcript.
- Can summarize notes with either a local extractive summarizer or an optional Ollama local LLM.
- Lets you choose the Markdown output folder per request.
- Provides a simple FastAPI frontend and JSON API.
- Saves a local watchlist of YouTube channels/playlists in SQLite.

## Requirements

- Python 3.11+
- `ffmpeg`
- `whisper.cpp` and a GGML Whisper model for local transcription

On macOS:

```bash
brew install ffmpeg whisper-cpp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Download a local model:

```bash
mkdir -p models
curl -L -o models/ggml-small.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin
```

## Configuration

Create a local `.env` file, which is ignored by Git:

```bash
READVIDEO_TRANSCRIPTION_BACKEND=local
READVIDEO_DOWNLOAD_DIR=downloads/youtube_videos
READVIDEO_NOTES_DIR=notes
READVIDEO_LOCAL_WHISPER_CLI=whisper-cli
READVIDEO_LOCAL_WHISPER_MODEL=models/ggml-small.bin
READVIDEO_LOCAL_WHISPER_LANGUAGE=zh
READVIDEO_NOTES_BACKEND=extractive
READVIDEO_OLLAMA_MODEL=qwen2.5:3b
READVIDEO_OLLAMA_URL=http://127.0.0.1:11434/api/generate
```

Optional Ollama note summaries:

```bash
ollama pull qwen2.5:3b
READVIDEO_NOTES_BACKEND=ollama
```

Optional OpenAI backend:

```bash
READVIDEO_TRANSCRIPTION_BACKEND=openai
OPENAI_API_KEY=sk-...
OPENAI_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
READVIDEO_CHUNK_SECONDS=180
```

The Google OAuth helper in `google_auth.py` is optional and only needed if you extend the project to call the YouTube Data API. Regular public video downloads use `yt-dlp` directly.

## Run

```bash
uvicorn main:app --reload
```

Open:

```text
http://localhost:8000
```

## API Usage

Create a background task:

```bash
curl -X POST "http://localhost:8000/process_video/" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "demo-1",
    "url": "https://www.youtube.com/watch?v=<VIDEO_ID>",
    "notes_dir": "/Users/you/Documents/Notes",
    "notes_backend": "extractive",
    "ollama_model": "qwen2.5:3b"
  }'
```

Check task status:

```bash
curl "http://localhost:8000/task_status/demo-1"
```

Watchlist:

```bash
curl "http://localhost:8000/watchlist"
```

## Tests

```bash
python -m unittest
```

## Project Structure

- `main.py`: FastAPI app, frontend, task lifecycle, and watchlist endpoints.
- `config.py`: Environment and legacy `apiKey.json` configuration.
- `local_transcription.py`: Local `whisper.cpp` transcription backend.
- `notes.py`: Transcript chunking, summary extraction, and Markdown note writing.
- `watchlist.py`: SQLite storage for YouTube channels/playlists.
- `yt_dl.py`: `yt-dlp` download wrapper.
- `audioTranscription.py`: Optional OpenAI transcription backend.
- `google_auth.py`: Optional YouTube Data API OAuth helper.
