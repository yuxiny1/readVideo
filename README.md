# readVideo

Download a YouTube video, transcribe its audio, turn the transcript into Markdown notes, and keep a small local watchlist of YouTube channels/playlists.

Apple Silicon uses the full MLX Whisper large-v3 model for high-quality local transcription. Containers keep `whisper.cpp`, and OpenAI access is optional.

## What It Does

- Downloads a single YouTube video with `yt-dlp`.
- Transcribes speech in the original language; it does not translate between languages.
- Supports MLX Whisper, `whisper.cpp`, and optional OpenAI transcription.
- Saves the raw transcript next to the downloaded video.
- Creates a Markdown note with key points, a narrative summary paragraph, and segmented notes; the raw transcript stays in its own `.txt` file instead of being embedded in the note.
- Creates Better Local AI Notes with Ollama by default.
- Lets you choose the Markdown output folder per request.
- Provides a simple FastAPI frontend and JSON API.
- Saves a local watchlist of YouTube channels/playlists in SQLite.

## Requirements

- Python 3.11+
- `ffmpeg`
- Apple Silicon: `mlx-whisper`; containers and other systems: `whisper.cpp`

On macOS:

```bash
brew install ffmpeg whisper-cpp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm run mlx:whisper:install
npm run mlx:whisper:download
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
READVIDEO_TRANSCRIPTION_BACKEND=mlx
READVIDEO_DOWNLOAD_DIR=downloads/youtube_videos
READVIDEO_NOTES_DIR=notes
READVIDEO_LOCAL_WHISPER_CLI=whisper-cli
READVIDEO_LOCAL_WHISPER_MODEL=models/ggml-large-v3.bin
READVIDEO_LOCAL_WHISPER_LANGUAGE=auto
READVIDEO_MLX_WHISPER_PYTHON=~/mlx-env/bin/python
READVIDEO_MLX_WHISPER_MODEL=mlx-community/whisper-large-v3-mlx
READVIDEO_NOTES_BACKEND=ollama
READVIDEO_OLLAMA_MODEL=qwen3.6:35b
READVIDEO_OLLAMA_URL=http://127.0.0.1:11434/api/generate
READVIDEO_MLX_MODEL=mlx-community/Qwen2.5-72B-Instruct-3bit
READVIDEO_MLX_URL=http://127.0.0.1:8080/v1/chat/completions
```

Default Ollama article-style notes:

```bash
ollama pull qwen3.6:35b
READVIDEO_NOTES_BACKEND=ollama
```

`READVIDEO_NOTES_BACKEND=ollama` means Better Local AI Notes: slower, but uses a local Ollama model to turn the full transcript into key points, a narrative summary paragraph, and high-detail article-style sections that preserve names, dates, examples, numbers, and the original flow. The default model is `qwen3.6:35b` when available.

On Apple Silicon, readVideo can use an MLX model instead of Ollama. After the Hugging Face download finishes, start the local server in a separate terminal with `npm run mlx:serve`, open readVideo, and select `MLX（Apple 芯片）` under `笔记生成引擎`. Use `npm run mlx:chat` when you only want an interactive terminal chat. See [MLX Local Model](docs/mlx-local-model.md) for download checks, container access, and troubleshooting.

For audio transcription, select `MLX Whisper（Apple 芯片，高精度）`. This uses the separate full large-v3 speech model directly and does not require `mlx_lm.server`. See [MLX Whisper Transcription](docs/mlx-whisper-transcription.md).

Optional OpenAI backend:

```bash
READVIDEO_TRANSCRIPTION_BACKEND=openai
OPENAI_API_KEY=sk-...
OPENAI_TRANSCRIPTION_MODEL=gpt-4o-mini-transcribe
READVIDEO_CHUNK_SECONDS=180
```

The Google OAuth helper in `google_auth.py` is optional and only needed if you extend the project to call the YouTube Data API. Regular public video downloads use `yt-dlp` directly.

## Run

### Container platform

The recommended full-stack setup runs Angular, FastAPI, the task worker, PostgreSQL, Redis, Ollama, and Portainer together:

```bash
cp deploy/container.env.example .container-env
npm run containers:up
npm run containers:migrate
npm run containers:pull-model -- qwen3.6:35b
```

Open `http://localhost:8080` for readVideo and `https://localhost:9443` for Portainer. See [Container Platform](docs/container-platform.md) for GPU VM deployment, management, migration, and backup instructions.
On macOS with an existing native Ollama installation, use `npm run containers:up:host-ollama` to keep Metal acceleration and reuse installed models.

### Local process

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
    "notes_backend": "ollama",
    "ollama_model": "qwen3.6:35b"
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
- `backend/application/`: CQRS Commands, Queries, Handlers, and Mediator dispatch.
- `backend/core/`: Settings and task state.
- `backend/services/`: Download, transcription, video processing, Ollama model checks, note generation, Markdown file listing, and saved source update discovery.
- `backend/storage/`: SQLAlchemy-backed history, favorites, tags, and watchlist storage for SQLite or PostgreSQL.
- `compose.yml`: Full application platform and persistent services.
- `deploy/`: Backend/frontend images, Nginx routing, and container environment example.
- `frontend/angular/`: Angular TypeScript application source.
- `frontend/angular/src/styles.css`: Global design tokens and native control primitives; feature styles are colocated with their Angular components.
- `config/`: Environment examples and local env files.
- `docs/`: Project documentation.
- `tests/`: Unit tests.
