from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

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


@app.exception_handler(RequestValidationError)
async def request_validation_error(_request: Request, exc: RequestValidationError):
    messages = {
        "missing": "缺少必填参数。",
        "string_too_short": "文本内容太短。",
        "url_parsing": "网址格式不正确。",
        "list_too_short": "列表内容不足。",
        "greater_than_equal": "数值低于允许范围。",
        "less_than_equal": "数值超过允许范围。",
        "bool_parsing": "布尔值格式不正确。",
    }
    errors = [
        {
            "field": ".".join(str(part) for part in error.get("loc", [])[1:]),
            "message": messages.get(str(error.get("type", "")), "参数格式不正确。"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": "请求参数无效。", "errors": errors})


@app.exception_handler(StarletteHTTPException)
async def http_error(_request: Request, exc: StarletteHTTPException):
    default_messages = {
        "Not Found": "找不到请求的资源。",
        "Method Not Allowed": "此地址不支持当前请求方法。",
    }
    detail = default_messages.get(str(exc.detail), exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": detail}, headers=exc.headers)


def angular_index():
    if ANGULAR_INDEX.exists():
        return FileResponse(ANGULAR_INDEX)
    return HTMLResponse(
        "Angular 前端尚未构建，请运行：npm install && npm run build:frontend",
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
