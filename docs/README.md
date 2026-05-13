# readVideo

Download a YouTube video, transcribe its audio, turn the transcript into Markdown notes, and keep a small local watchlist of YouTube channels/playlists.

The default transcription backend is local `whisper.cpp`, so OpenAI API access is optional.

## What It Does

- Downloads a single YouTube video with `yt-dlp`.
- Transcribes speech in the original language; it does not translate between languages.
- Uses local `whisper.cpp` by default, with optional OpenAI transcription support.
- Lets you choose transcription backend, spoken-language detection, prompt terms, and larger local Whisper models per run.
- Saves the raw transcript next to the downloaded video.
- Creates a Markdown note with summary, structured sections, and full transcript.
- Can summarize notes with either a local extractive summarizer or an optional Ollama local LLM.
- Uses a full-transcript chunk-and-combine workflow for Ollama summaries so long videos are not summarized from only an excerpt.
- Lets you choose or pull larger Ollama models from the browser when you want stronger local summaries.
- Lets you choose the Markdown output folder per request.
- Provides a simple FastAPI frontend and JSON API.
- Shows recent task status, elapsed time, and generated output paths in the browser.
- Persists processed video history in SQLite, including source URL, video, transcript, and Markdown paths.
- Lets you search favorite summaries and keep their Markdown locations in one page.
- Lets you open, favorite, or copy a summary from the current Latest Output panel after a download finishes, with optional folder assignment from History.
- Lets you open favorite Markdown notes in a dedicated reader page.
- Lets you create virtual note folders for favorite Markdown notes without moving the original files on disk.
- Lists Markdown files from a chosen notes folder and serves them for reading or download.
- Saves a local watchlist of YouTube channels/playlists in SQLite, supports manual drag ordering and alternate sort views, and can check recent source updates with `yt-dlp`.

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
READVIDEO_LOCAL_WHISPER_LANGUAGE=auto
READVIDEO_LOCAL_WHISPER_PROMPT=
READVIDEO_LOCAL_WHISPER_AUDIO_FILTER=highpass=f=80,lowpass=f=8000,loudnorm=I=-16:TP=-1.5:LRA=11
READVIDEO_LOCAL_WHISPER_CHUNK_SECONDS=60
READVIDEO_NOTES_BACKEND=extractive
READVIDEO_OLLAMA_MODEL=qwen2.5:3b
READVIDEO_OLLAMA_URL=http://127.0.0.1:11434/api/generate
```

`READVIDEO_LOCAL_WHISPER_MODEL` is the audio transcription model. If you do not set it, the app picks the strongest installed local model in this order: `ggml-large-v3-turbo.bin`, `ggml-medium.bin`, `ggml-small.bin`, then `ggml-base.bin`. `READVIDEO_LOCAL_WHISPER_LANGUAGE=auto` is recommended for YouTube because forcing `zh` on English or mixed-language videos can produce Chinese-looking nonsense text.

For better local transcription quality, use the browser model picker or download a larger GGML model manually:

```bash
curl -L -o models/ggml-medium.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium.bin
curl -L -o models/ggml-large-v3-turbo.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
```

`READVIDEO_LOCAL_WHISPER_PROMPT` can contain names and technical terms that appear in the video, such as `Jim Keller, CUDA, OpenAI`. The app automatically adds the video title to the transcription prompt, applies a light speech audio filter before local transcription, and transcribes local audio in chunks. This is much more reliable for long YouTube videos and reduces silence/outro hallucinations.

`READVIDEO_OLLAMA_MODEL` is only used for Markdown summary and note organization when `READVIDEO_NOTES_BACKEND=ollama`. It does not transcribe audio.

Optional Ollama note summaries:

```bash
ollama pull qwen2.5:3b
READVIDEO_NOTES_BACKEND=ollama
```

The frontend includes recommended Ollama summary models. Lighter models are faster; larger models usually produce better structure and summaries if your machine has enough memory.

```bash
ollama pull qwen2.5:7b
ollama pull qwen2.5:14b
ollama pull qwen3:14b
ollama pull llama3.1:8b
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
python main.py
```

The app will start on the first available port beginning at `8000` and print the URL, for example:

```text
Starting readVideo on http://127.0.0.1:8000
```

The frontend is served from `frontend/` and calls the same FastAPI app for task status, Markdown output, and saved YouTube sources. Main navigation lives in the left sidebar.
Open `/history` to review previously downloaded/transcribed videos and their saved file paths.
Open `/favorites` to search favorite summaries, organize them into note folders, jump to their Markdown folders, list `.md` files, and download notes.
Open `/reader` to read favorite Markdown notes in a focused page with a left-side searchable note list and folder selector.

## API Usage

Create a background task:

```bash
curl -X POST "http://localhost:8000/process_video/" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "demo-1",
    "url": "https://www.youtube.com/watch?v=<VIDEO_ID>",
    "transcription_backend": "local",
    "local_whisper_model": "models/ggml-large-v3-turbo.bin",
    "local_whisper_language": "auto",
    "transcription_prompt": "Jim Keller, CUDA, OpenAI",
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
curl -X PATCH "http://localhost:8000/watchlist/1" \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated source", "url": "https://www.youtube.com/@example", "notes": "Weekly"}'
curl -X PATCH "http://localhost:8000/watchlist/reorder" \
  -H "Content-Type: application/json" \
  -d '{"item_ids": [3, 1, 2]}'
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
  -d '{"task_id": "demo-1", "folder_id": 1}'
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

Ollama local summary models:

```bash
curl "http://localhost:8000/api/ollama/models"
curl -X POST "http://localhost:8000/api/ollama/pull" \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen3:14b"}'
```

Transcription model options:

```bash
curl "http://localhost:8000/api/transcription/models"
curl -X POST "http://localhost:8000/api/transcription/models/download" \
  -H "Content-Type: application/json" \
  -d '{"model": "ggml-large-v3-turbo.bin"}'
```

## Tests

```bash
python -m unittest discover -s tests
node --test frontend/tests/*.test.js
```

## Project Structure

- `main.py`: Thin backwards-compatible entrypoint for `uvicorn main:app`.
- `backend/app.py`: FastAPI app factory surface, frontend mounting, router registration.
- `backend/api/`: HTTP routes and request schemas.
- `backend/core/`: Settings and task state.
- `backend/services/`: Download, transcription, video processing, note generation, Markdown file listing, and saved source update discovery.
- `backend/storage/`: SQLite-backed watchlist, processing history, and favorite summary storage.
- `frontend/html/`: Browser HTML.
- `frontend/css/`: Browser styles.
- `frontend/js/`: Browser behavior and API calls.
- `config/`: Environment examples and local env files.
- `docs/`: Project documentation.
- `tests/`: Unit tests.
