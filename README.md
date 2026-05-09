# readVideo

Download a YouTube video, extract its audio, and transcribe it with the OpenAI audio transcription API through a small FastAPI service.

## What It Does

- Downloads a single video with `yt-dlp`.
- Converts the video audio to WAV with MoviePy/ffmpeg.
- Splits longer audio into chunks before sending it to OpenAI.
- Transcribes speech in the original language; it does not translate between languages.
- Saves the transcript next to the downloaded video.
- Exposes task creation and task status endpoints with FastAPI.

## Requirements

- Python 3.11+
- ffmpeg installed on your system
- An OpenAI API key

On macOS:

```bash
brew install ffmpeg
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Prefer environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export READVIDEO_DOWNLOAD_DIR="downloads/youtube_videos"
export OPENAI_TRANSCRIPTION_MODEL="whisper-1"
export READVIDEO_CHUNK_SECONDS="180"
```

For backwards compatibility, the app also accepts an `apiKey.json` file:

```json
{
  "apiKey": "sk-..."
}
```

The Google OAuth helper in `google_auth.py` is optional and only needed if you extend the project to call the YouTube Data API. Regular public video downloads use `yt-dlp` directly.

## Run

```bash
uvicorn main:app --reload
```

## Usage

Create a background task:

```bash
curl -X POST "http://localhost:8000/process_video/" \
  -H "Content-Type: application/json" \
  -d '{"task_id": "demo-1", "url": "https://www.youtube.com/watch?v=<VIDEO_ID>"}'
```

Check task status:

```bash
curl "http://localhost:8000/task_status/demo-1"
```

Health check:

```bash
curl "http://localhost:8000/health"
```

## Tests

```bash
python -m unittest
```

## Project Structure

- `main.py`: FastAPI app, task lifecycle, and configuration loading.
- `config.py`: Environment and legacy `apiKey.json` configuration.
- `yt_dl.py`: `yt-dlp` download wrapper.
- `audioTranscription.py`: Audio extraction, chunking, transcription, and cleanup.
- `google_auth.py`: Optional YouTube Data API OAuth helper.
- `test_transcription.py`: Offline unit tests for transcription helpers.
