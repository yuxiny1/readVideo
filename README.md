# readVideo

Download a YouTube video, transcribe its audio, turn the transcript into Markdown notes, and keep a small local watchlist of YouTube channels/playlists.

Apple Silicon uses the full MLX Whisper large-v3 model for high-quality local transcription. Containers keep `whisper.cpp`, and OpenAI access is optional.

## Which Local Model Does What?

readVideo can use several local runtimes at the same time. They are separate jobs and should not be confused:

| Job | Runtime | Recommended/current model | Server required? |
| --- | --- | --- | --- |
| Audio to text | MLX Whisper | `mlx-community/whisper-large-v3-mlx` | No; readVideo starts it directly |
| Markdown summaries (default) | Ollama | `qwen3.6:35b` | Yes, Ollama on `127.0.0.1:11434` |
| Markdown summaries (Apple Silicon alternative) | OMLX | `Qwen2.5-14B-Instruct-4bit` | Yes, OMLX on `127.0.0.1:8000` |
| Compatibility transcription | whisper.cpp | `models/ggml-large-v3.bin` | No; readVideo runs the CLI |

OMLX is an OpenAI-compatible MLX model server. It is not the same thing as MLX Whisper. OMLX loads a language model only when a request arrives, so a healthy server may correctly report `loaded_count: 0` while idle.

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

## Start From Zero (Apple Silicon Mac)

### 1. Install system tools

You need Python 3.11+, Node.js 24, npm 11, `ffmpeg`, and at least one note-generation runtime.

```bash
brew install ffmpeg whisper-cpp

# Install nvm once if it is not already available.
brew install nvm
mkdir -p "$HOME/.nvm"
export NVM_DIR="$HOME/.nvm"
source /opt/homebrew/opt/nvm/nvm.sh
```

Install Ollama from the official macOS app, or with Homebrew:

```bash
brew install ollama
brew services start ollama
```

OMLX is optional. Install it only when you want Apple Silicon MLX language-model summaries:

```bash
brew install omlx
brew services start omlx
```

OMLX uses port `8000`. When it is running, readVideo automatically starts on the next free port, usually `8001`.

### 2. Clone and install readVideo

```bash
git clone https://github.com/yuxiny1/readVideo.git
cd readVideo

nvm install
nvm use

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
npm install
```

### 3. Install MLX Whisper for transcription

```bash
python3 -m venv ~/mlx-env
~/mlx-env/bin/python -m pip install --upgrade pip mlx-lm mlx-whisper huggingface-hub
npm run mlx:whisper:install
npm run mlx:whisper:download
```

The model is cached outside the repository under the Hugging Face cache. It is downloaded once and reused.

For a non-Apple system or a whisper.cpp fallback, download the GGML model instead:

```bash
mkdir -p models
curl -L -o models/ggml-large-v3.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3.bin
```

### 4. Install a note model

The default path uses Ollama:

```bash
ollama pull qwen3.6:35b
ollama list
```

For OMLX, open `http://127.0.0.1:8000/admin/dashboard`, download a supported text model, and set it as the default. The documented lightweight default is `Qwen2.5-14B-Instruct-4bit`. OMLX manages its models under `~/.omlx/models/`.

### 5. Create local configuration

```bash
cp config/env.example config/.env
```

The checked-in example is safe to copy. `config/.env` is ignored by Git. Never commit API keys, downloaded media, transcripts, local notes, databases, or model files.

## Configuration

The default Apple Silicon setup is:

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
READVIDEO_NOTE_STYLE=detailed
READVIDEO_OLLAMA_MODEL=qwen3.6:35b
READVIDEO_OLLAMA_URL=http://127.0.0.1:11434/api/generate
READVIDEO_MLX_MODEL=Qwen2.5-14B-Instruct-4bit
READVIDEO_MLX_URL=http://127.0.0.1:8000/v1/chat/completions
```

The app reads `config/.env` after a root `.env`, so `config/.env` wins when both files define the same setting.

Default Ollama article-style notes:

```bash
ollama pull qwen3.6:35b
READVIDEO_NOTES_BACKEND=ollama
```

`READVIDEO_NOTES_BACKEND=ollama` means Better Local AI Notes: slower, but uses a local Ollama model to turn the full transcript into key points, a narrative summary paragraph, and high-detail article-style sections that preserve names, dates, examples, numbers, and the original flow. The default model is `qwen3.6:35b` when available.

On Apple Silicon, readVideo can use OMLX instead of Ollama. Start OMLX, open readVideo, and select `MLX（Apple 芯片）` under `笔记生成引擎`. OMLX exposes the OpenAI-compatible endpoint configured by `READVIDEO_MLX_URL`. The older `mlx_lm.server` workflow remains available through `npm run mlx:serve` on port `8080`. See [MLX Local Model](docs/mlx-local-model.md) for both workflows.

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
npm run build:frontend
npm run dev
```

The app will start on the first available port starting at `8000` and print the URL, for example:

```text
Starting readVideo on http://127.0.0.1:8000
```

If port `8000` is already in use, it automatically falls back to the next available port.

The equivalent explicit commands are:

```bash
npm install
npm run build:frontend
.venv/bin/python main.py
```

FastAPI serves the Angular app for `/`, `/history`, `/favorites`, and `/reader`.
If the Angular build output is not present, those routes return a clear `503` telling you to run `npm run build:frontend`.

You can also request a specific port:

```bash
python main.py --port 8000
```

If OMLX already owns port `8000`, use `8001` or let readVideo choose automatically:

```bash
.venv/bin/python main.py --port 8001
```

## Check the Active Models

Check the settings readVideo will actually use (this does not print API keys):

```bash
.venv/bin/python -c "from backend.core.config import load_settings; s=load_settings(); print('transcription_backend=', s.transcription_backend); print('mlx_whisper_model=', s.mlx_whisper_model); print('notes_backend=', s.notes_backend); print('ollama_model=', s.ollama_model); print('mlx_model=', s.mlx_model); print('mlx_url=', s.mlx_url)"
```

Check Ollama:

```bash
ollama list
curl -fsS http://127.0.0.1:11434/api/tags
```

Check OMLX health, the default model, installed models, and memory-loaded state:

```bash
npm run omlx:status
npm run omlx:models

# Pretty-printed alternatives:
curl -fsS http://127.0.0.1:8000/health | python3 -m json.tool
curl -fsS http://127.0.0.1:8000/v1/models | python3 -m json.tool
curl -fsS http://127.0.0.1:8000/v1/models/status | python3 -m json.tool
```

The OMLX admin interface is at `http://127.0.0.1:8000/admin/dashboard`. A model with `loaded: false` is installed but currently idle; it will be loaded when selected and called.

Check the MLX Whisper environment and cached model:

```bash
~/mlx-env/bin/python -c "import mlx_whisper; print('mlx-whisper ready')"
find ~/.cache/huggingface/hub -maxdepth 1 -type d -name 'models--mlx-community--whisper*'
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
READVIDEO_BASE_URL=http://127.0.0.1:8001

curl -X POST "$READVIDEO_BASE_URL/process_video/" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "demo-1",
    "url": "https://www.youtube.com/watch?v=<VIDEO_ID>",
    "notes_dir": "/Users/you/Documents/Notes",
    "notes_backend": "ollama",
    "note_style": "commercial",
    "ollama_model": "qwen3.6:35b",
    "delete_video_after_completion": true
  }'
```

Set `READVIDEO_BASE_URL` to the URL printed by readVideo at startup. It is usually `http://127.0.0.1:8001` when OMLX already owns port `8000`, and `http://127.0.0.1:8000` otherwise.

Check task status:

```bash
curl "$READVIDEO_BASE_URL/task_status/demo-1"
```

Watchlist:

```bash
curl "$READVIDEO_BASE_URL/watchlist"
```

## Tests

```bash
npm run check
```

Focused commands are also available:

```bash
npm test
npm run test:coverage
npm run test:frontend:coverage
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
