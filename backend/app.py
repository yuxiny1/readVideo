from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
HTML_DIR = FRONTEND_DIR / "html"

app = FastAPI(title="readVideo")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
app.include_router(router)


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(HTML_DIR / "index.html")


@app.get("/history", include_in_schema=False)
async def history_page():
    return FileResponse(HTML_DIR / "history.html")


@app.get("/favorites", include_in_schema=False)
async def favorites_page():
    return FileResponse(HTML_DIR / "favorites.html")


@app.get("/reader", include_in_schema=False)
async def reader_page():
    return FileResponse(HTML_DIR / "reader.html")
