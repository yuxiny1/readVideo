# readVideo

Download a YouTube video, transcribe its audio, turn the transcript into Markdown notes, and keep a small local watchlist of YouTube channels/playlists.

The default transcription backend is local `whisper.cpp`, so OpenAI API access is optional.
For local transcription quality, `ggml-large-v3-turbo.bin` is the recommended default; smaller models are faster but more likely to repeat or hallucinate text on noisy YouTube audio.

## What It Does

- Downloads a single YouTube video with `yt-dlp`.
- Transcribes speech in the original language; it does not translate between languages.
- Uses local `whisper.cpp` by default, with optional OpenAI transcription support.
- Saves the raw transcript next to the downloaded video.
- Creates a Markdown note with summary and segmented notes; the raw transcript stays in its own `.txt` file instead of being embedded in the note.
- Can create Quick Notes with simple local rules, or Better Local AI Notes with an optional Ollama model.
- Lets you choose the Markdown output folder per request.
- Can delete the downloaded local video after a successful run while keeping the transcript, Markdown note, and history.
- Provides a simple FastAPI frontend and JSON API.
- Shows recent task status, elapsed time, and generated output paths in the browser.
- Persists processed video history in SQLite, including source URL, video, transcript, and Markdown paths.
- Lets you favorite valuable summaries and keep their Markdown locations in one page.
- Lets you favorite a summary from either the History page or the current Latest Output panel after a download finishes.
- Lets you open favorite Markdown notes in a dedicated built-in reader without leaving the browser.
- Lets you create virtual note folders for favorite Markdown notes without moving the original files on disk.
- Lists Markdown files from a chosen notes folder and serves them for reading or download.
- Saves a local watchlist of YouTube channels/playlists in SQLite and can check recent source updates with `yt-dlp`.

## Requirements

- Python 3.11+
- Node.js 24 LTS with npm 11 for the Angular TypeScript frontend and shared project scripts
- `ffmpeg`
- `whisper.cpp` and a GGML Whisper model for local transcription

On macOS:

```bash
brew install ffmpeg whisper-cpp
nvm install
nvm use
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install
```

Download a local model:

```bash
mkdir -p models
curl -L -o models/ggml-large-v3-turbo.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
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
READVIDEO_LOCAL_WHISPER_MODEL=models/ggml-large-v3-turbo.bin
READVIDEO_LOCAL_WHISPER_LANGUAGE=auto
READVIDEO_NOTES_BACKEND=extractive
READVIDEO_OLLAMA_MODEL=qwen2.5:3b
READVIDEO_OLLAMA_URL=http://127.0.0.1:11434/api/generate
```

Optional Ollama note summaries:

```bash
ollama pull qwen2.5:3b
READVIDEO_NOTES_BACKEND=ollama
```

`READVIDEO_NOTES_BACKEND=extractive` means Quick Notes: fastest, no AI model needed. `READVIDEO_NOTES_BACKEND=ollama` means Better Local AI Notes: slower, but asks a local Ollama model to turn the full transcript into a readable summary plus article-style sections. The Markdown note no longer embeds the full transcript; the transcript remains available as its separate `.txt` output.

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
python main.py
```

The app will start on the first available port starting at `8000` and print the URL, for example:

```text
Starting readVideo on http://127.0.0.1:8000
```

If port `8000` is already in use, it automatically falls back to the next available port.

The frontend is an Angular TypeScript app under `frontend/angular/`. This repo pins Node 24 through `.nvmrc`, `.node-version`, and `package.json` engines; use that version for local servers, web app builds, command-line tools, and npm scripts. FastAPI serves the built app and the frontend calls the same FastAPI process for task status, history, favorites, Markdown output, and saved YouTube sources. Main navigation lives in the left sidebar.
Open `/history` to review previously downloaded/transcribed videos and their saved file paths.
Open `/favorites` to review favorite summaries and organize them into note folders.
Open `/reader` to switch between favorite folders, browse local Markdown folders, read `.md` files, and download notes.

Build the Angular app before starting FastAPI. If the build output is missing, FastAPI returns a clear `503` instead of serving stale legacy pages.

```bash
npm install
npm run build:frontend
python main.py
```

Useful Node-managed scripts:

```bash
npm run dev             # start the FastAPI app through package.json
npm run build           # build the Angular frontend
npm run check:frontend  # development Angular build/type check
npm test                # run the Python unit test suite from the active venv
```

The npm scripts expect the project virtualenv at `.venv/`, created in the setup steps above.

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
    "ollama_model": "qwen2.5:3b",
    "delete_video_after_completion": true
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

Favorites:

```bash
curl "http://localhost:8000/api/favorites"
curl -X POST "http://localhost:8000/api/favorites" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "demo-1"}'
```

Markdown files:

```bash
curl "http://localhost:8000/api/markdown_files?directory=notes"
curl "http://localhost:8000/api/markdown_files/read?path=notes/demo.md"
curl -OJ "http://localhost:8000/api/markdown_files/download?path=notes/demo.md"
```

Favorite folders:

```bash
curl "http://localhost:8000/api/favorites/folders"
curl -X POST "http://localhost:8000/api/favorites/folders" \
  -H "Content-Type: application/json" \
  -d '{"name": "AI notes", "notes": "Local model and agent videos"}'
curl -X PATCH "http://localhost:8000/api/favorites/1/folder" \
  -H "Content-Type: application/json" \
  -d '{"folder_id": 1}'
curl "http://localhost:8000/api/favorites/1/markdown"
```

Saved source updates:

```bash
curl "http://localhost:8000/watchlist/1/updates?limit=8"
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
- `backend/services/`: Download, transcription, video processing, note generation, Markdown file listing, and saved source update discovery.
- `backend/storage/`: SQLite-backed watchlist, processing history, and favorite summary storage.
- `frontend/angular/`: Angular TypeScript application source.
- `frontend/css/`: Shared Angular styles. `styles.css` is only the import manifest; page and component styles live in `frontend/css/partials/`.
- `config/`: Environment examples and local env files.
- `docs/`: Project documentation.
- `tests/`: Unit tests.
