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
python main.py
```

The app will start on the first available port starting at `8000` and print the URL, for example:

```text
Starting readVideo on http://127.0.0.1:8000
```

If port `8000` is already in use, it automatically falls back to the next available port.

Build the Angular frontend before starting FastAPI:

```bash
npm install
npm run build:frontend
python main.py
```

FastAPI serves the Angular app for `/`, `/history`, `/favorites`, and `/reader`.
If the Angular build output is not present, those routes return a clear `503` telling you to run `npm run build:frontend`.

You can also request a specific port:

```bash
python main.py --port 8000
```

## Troubleshooting

If the server cannot start, confirm your environment and dependencies:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

If another process is already listening on `8000`, stop it or use a different port:

```bash
lsof -i tcp:8000
kill <pid>
python main.py --port 8001
```

Also check for stray `uvicorn` processes:

```bash
ps aux | grep uvicorn
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

- `main.py`: Thin backwards-compatible entrypoint for `uvicorn main:app`.
- `backend/app.py`: FastAPI app, Angular static mounting, page routes, and router registration.
- `backend/api/`: HTTP routes and request schemas.
- `backend/core/`: Settings and task state.
- `backend/services/`: Download, transcription, video processing, Ollama model checks, note generation, Markdown file listing, and saved source update discovery.
- `backend/storage/`: SQLite-backed watchlist, processing history, and favorite summary storage.
- `frontend/angular/`: Angular TypeScript application source.
- `frontend/css/`: Shared app styles imported by Angular.
- `config/`: Environment examples and local env files.
- `docs/`: Project documentation.
- `tests/`: Unit tests.
