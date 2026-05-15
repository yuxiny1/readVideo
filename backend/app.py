from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import router


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = PROJECT_ROOT / "frontend"
ANGULAR_DIST_DIR = FRONTEND_DIR / "dist" / "readvideo" / "browser"
ANGULAR_INDEX = ANGULAR_DIST_DIR / "index.html"

app = FastAPI(title="readVideo")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
if ANGULAR_DIST_DIR.exists():
    app.mount("/app", StaticFiles(directory=ANGULAR_DIST_DIR), name="angular")
app.include_router(router)


def angular_index():
    if ANGULAR_INDEX.exists():
        return FileResponse(ANGULAR_INDEX)
    return HTMLResponse(
        "Angular frontend is not built. Run: npm install && npm run build:frontend",
        status_code=503,
    )


@app.get("/", include_in_schema=False)
async def index():
    return angular_index()


@app.get("/history", include_in_schema=False)
async def history_page():
    return angular_index()


@app.get("/favorites", include_in_schema=False)
async def favorites_page():
    return angular_index()


@app.get("/reader", include_in_schema=False)
async def reader_page():
    return angular_index()
