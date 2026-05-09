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
- Shows recent task status, elapsed time, and generated output paths in the browser.
- Persists processed video history in SQLite, including video, transcript, and Markdown paths.
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

Create `config/.env` from the checked-in example:

```bash
cp config/env.example config/.env
```

The app also still reads a root `.env` for backwards compatibility. The main settings are:

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

The Google OAuth helper in `backend/services/google_auth.py` is optional and only needed if you extend the project to call the YouTube Data API. Regular public video downloads use `yt-dlp` directly.

## Run

```bash
uvicorn backend.app:app --reload
```

Open:

```text
http://localhost:8000
```

The frontend is served from `frontend/` and calls the same FastAPI app for task status, Markdown output, and saved YouTube sources.
Open `/history` to review previously downloaded/transcribed videos and their saved file paths.

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

History:

```bash
curl "http://localhost:8000/api/history"
```

## Tests

```bash
python -m unittest discover -s tests
```

## Project Structure

- `main.py`: Thin backwards-compatible entrypoint for `uvicorn main:app`.
- `backend/app.py`: FastAPI app factory surface, frontend mounting, router registration.
- `backend/api/`: HTTP routes and request schemas.
- `backend/core/`: Settings and task state.
- `backend/services/`: Download, transcription, video processing, and note generation.
- `backend/storage/`: SQLite-backed watchlist and processing history storage.
- `frontend/html/`: Browser HTML.
- `frontend/css/`: Browser styles.
- `frontend/js/`: Browser behavior and API calls.
- `config/`: Environment examples and local env files.
- `docs/`: Project documentation.
- `tests/`: Unit tests.
