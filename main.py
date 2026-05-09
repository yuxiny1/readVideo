import asyncio
import logging
from typing import Optional
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, HttpUrl

from audioTranscription import AudioTranscription
from config import Settings, load_settings
from local_transcription import LocalWhisperTranscription
from notes import write_markdown_note
from watchlist import WatchlistStore
from yt_dl import download_video


logger = logging.getLogger(__name__)
app = FastAPI(title="readVideo")
TASKS = {}


class ProcessVideoRequest(BaseModel):
    url: HttpUrl
    task_id: Optional[str] = Field(default=None, min_length=1)
    notes_dir: Optional[str] = Field(default=None, min_length=1)
    notes_backend: Optional[str] = Field(default=None, min_length=1)
    ollama_model: Optional[str] = Field(default=None, min_length=1)


class WatchItemRequest(BaseModel):
    name: str = Field(min_length=1)
    url: HttpUrl
    notes: str = ""


def set_task_status(task_id: str, status: str, **details):
    TASKS[task_id] = {"task_id": task_id, "status": status, **details}


def get_store() -> WatchlistStore:
    return WatchlistStore(load_settings().database_path)


def transcribe_video(video_path: str, settings: Settings):
    if settings.transcription_backend == "local":
        service = LocalWhisperTranscription(
            whisper_cli=settings.local_whisper_cli,
            model_path=settings.local_whisper_model,
            language=settings.local_whisper_language,
        )
        return service.process_video(video_path)

    service = AudioTranscription(
        api_key=settings.openai_api_key,
        model=settings.transcription_model,
    )
    return service.process_video(video_path, settings.chunk_seconds)


async def process_video(
    task_id: str,
    url: str,
    notes_dir: Optional[str] = None,
    notes_backend: Optional[str] = None,
    ollama_model: Optional[str] = None,
):
    try:
        settings = load_settings()
        resolved_notes_backend = _resolve_notes_backend(notes_backend, settings.notes_backend)
        resolved_ollama_model = ollama_model or settings.ollama_model
        set_task_status(task_id, "downloading", url=url)

        downloaded_file_path = await asyncio.to_thread(download_video, url, settings.download_dir)
        set_task_status(task_id, "transcribing", url=url, video_path=downloaded_file_path)

        result = await asyncio.to_thread(transcribe_video, downloaded_file_path, settings)
        set_task_status(
            task_id,
            "organizing_notes",
            url=url,
            video_path=downloaded_file_path,
            transcription_path=result.transcription_path,
        )

        video_title = _title_from_path(downloaded_file_path)
        note_result = await asyncio.to_thread(
            write_markdown_note,
            result.text,
            video_title,
            url,
            notes_dir or settings.notes_dir,
            result.transcription_path,
            resolved_notes_backend,
            resolved_ollama_model,
            settings.ollama_url,
        )

        set_task_status(
            task_id,
            "completed",
            url=url,
            video_path=downloaded_file_path,
            transcription_path=result.transcription_path,
            markdown_path=note_result.markdown_path,
            summary=note_result.summary,
            section_count=note_result.section_count,
            transcription_backend=settings.transcription_backend,
            summary_backend=note_result.summary_backend,
            ollama_model=resolved_ollama_model if resolved_notes_backend == "ollama" else None,
            chunk_count=getattr(result, "chunk_count", None),
        )
    except Exception as exc:
        logger.exception("Task %s failed", task_id)
        set_task_status(task_id, "failed", url=url, error=str(exc))


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(INDEX_HTML)


@app.post("/process_video/")
async def create_task(request: ProcessVideoRequest, background_tasks: BackgroundTasks):
    try:
        settings = load_settings()
        _resolve_notes_backend(request.notes_backend, settings.notes_backend)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    task_id = request.task_id or str(uuid4())
    set_task_status(task_id, "queued", url=str(request.url))
    background_tasks.add_task(
        process_video,
        task_id,
        str(request.url),
        request.notes_dir,
        request.notes_backend,
        request.ollama_model,
    )

    return {
        "task_id": task_id,
        "status": "queued",
        "status_url": f"/task_status/{task_id}",
    }


@app.get("/task_status/{task_id}")
async def get_task_status(task_id: str):
    task = TASKS.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/watchlist")
async def list_watchlist():
    return [item.__dict__ for item in get_store().list_items()]


@app.post("/watchlist")
async def add_watch_item(request: WatchItemRequest):
    item = get_store().add_item(request.name, str(request.url), request.notes)
    return item.__dict__


@app.delete("/watchlist/{item_id}")
async def delete_watch_item(item_id: int):
    deleted = get_store().delete_item(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Watch item not found")
    return {"deleted": True}


@app.get("/health")
async def health():
    return {"status": "ok"}


def _title_from_path(path: str) -> str:
    from pathlib import Path

    return Path(path).stem


def _resolve_notes_backend(request_backend: Optional[str], default_backend: str) -> str:
    backend = (request_backend or default_backend).lower()
    if backend not in {"extractive", "ollama"}:
        raise RuntimeError("notes_backend must be extractive or ollama.")
    return backend


INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>readVideo</title>
  <style>
    :root { color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #1e2430; }
    header { padding: 24px 32px 12px; border-bottom: 1px solid #d9dee8; background: #fff; }
    h1 { margin: 0; font-size: 28px; letter-spacing: 0; }
    main { max-width: 1120px; margin: 0 auto; padding: 24px 20px 48px; display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(320px, 0.8fr); gap: 20px; }
    section { background: #fff; border: 1px solid #d9dee8; border-radius: 8px; padding: 18px; }
    h2 { margin: 0 0 14px; font-size: 17px; letter-spacing: 0; }
    label { display: block; margin: 12px 0 6px; font-size: 13px; font-weight: 650; color: #4a5260; }
    input, textarea, select { width: 100%; box-sizing: border-box; border: 1px solid #c5ccd8; border-radius: 6px; padding: 10px 12px; font: inherit; background: #fff; }
    textarea { min-height: 72px; resize: vertical; }
    button { margin-top: 14px; border: 0; border-radius: 6px; padding: 10px 14px; font: inherit; font-weight: 700; background: #135cc8; color: #fff; cursor: pointer; }
    button.secondary { background: #e8edf5; color: #243044; }
    button.danger { background: #b42318; }
    pre { min-height: 180px; white-space: pre-wrap; word-break: break-word; background: #101828; color: #e7edf8; border-radius: 6px; padding: 14px; overflow: auto; }
    .row { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    .watch-item { border-top: 1px solid #edf0f5; padding: 12px 0; }
    .watch-item strong { display: block; margin-bottom: 4px; }
    .watch-item a { color: #135cc8; word-break: break-all; }
    @media (max-width: 800px) { main { grid-template-columns: 1fr; padding: 16px; } header { padding: 20px 16px 10px; } }
  </style>
</head>
<body>
  <header>
    <h1>readVideo</h1>
  </header>
  <main>
    <section>
      <h2>Process Video</h2>
      <form id="process-form">
        <label for="url">YouTube URL</label>
        <input id="url" name="url" required placeholder="https://www.youtube.com/watch?v=...">
        <label for="notes-dir">Markdown output folder</label>
        <input id="notes-dir" name="notes_dir" placeholder="notes or /Users/you/Library/Mobile Documents/...">
        <label for="notes-backend">Summary backend</label>
        <select id="notes-backend" name="notes_backend">
          <option value="extractive">Local extractive</option>
          <option value="ollama">Ollama local LLM</option>
        </select>
        <label for="ollama-model">Ollama model</label>
        <input id="ollama-model" name="ollama_model" placeholder="qwen2.5:3b">
        <button type="submit">Start</button>
      </form>
      <h2 style="margin-top:22px">Task Status</h2>
      <pre id="status">Idle</pre>
    </section>
    <section>
      <h2>Watchlist</h2>
      <form id="watch-form">
        <label for="watch-name">Name</label>
        <input id="watch-name" required placeholder="Channel or playlist name">
        <label for="watch-url">URL</label>
        <input id="watch-url" required placeholder="https://www.youtube.com/@...">
        <label for="watch-notes">Notes</label>
        <textarea id="watch-notes" placeholder="Why you follow it"></textarea>
        <button type="submit">Save</button>
      </form>
      <div id="watchlist"></div>
    </section>
  </main>
  <script>
    const statusEl = document.querySelector("#status");
    const urlEl = document.querySelector("#url");
    const watchlistEl = document.querySelector("#watchlist");

    function showStatus(value) {
      statusEl.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
    }

    async function pollTask(taskId) {
      const response = await fetch(`/task_status/${taskId}`);
      const data = await response.json();
      showStatus(data);
      if (!["completed", "failed"].includes(data.status)) {
        setTimeout(() => pollTask(taskId), 2000);
      }
    }

    document.querySelector("#process-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = {
        url: urlEl.value,
        notes_dir: document.querySelector("#notes-dir").value || null,
        notes_backend: document.querySelector("#notes-backend").value,
        ollama_model: document.querySelector("#ollama-model").value || null
      };
      showStatus("Queued...");
      const response = await fetch("/process_video/", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      showStatus(data);
      if (response.ok) pollTask(data.task_id);
    });

    document.querySelector("#watch-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const payload = {
        name: document.querySelector("#watch-name").value,
        url: document.querySelector("#watch-url").value,
        notes: document.querySelector("#watch-notes").value
      };
      await fetch("/watchlist", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });
      event.target.reset();
      loadWatchlist();
    });

    async function deleteWatchItem(id) {
      await fetch(`/watchlist/${id}`, {method: "DELETE"});
      loadWatchlist();
    }

    async function loadWatchlist() {
      const response = await fetch("/watchlist");
      const items = await response.json();
      watchlistEl.innerHTML = items.map(item => `
        <div class="watch-item">
          <strong>${escapeHtml(item.name)}</strong>
          <a href="${escapeHtml(item.url)}" target="_blank">${escapeHtml(item.url)}</a>
          <p>${escapeHtml(item.notes || "")}</p>
          <div class="row">
            <button class="secondary" onclick="urlEl.value='${escapeAttr(item.url)}'">Use</button>
            <button class="danger" onclick="deleteWatchItem(${item.id})">Delete</button>
          </div>
        </div>
      `).join("");
    }

    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}[c]));
    }

    function escapeAttr(value) {
      return String(value).replace(/['\\\\]/g, "\\\\$&");
    }

    loadWatchlist();
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
