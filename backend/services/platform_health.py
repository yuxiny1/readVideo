from sqlalchemy import text

from backend.core.config import Settings
from backend.services.ollama_models import list_ollama_models
from backend.storage.database import database_engine


def inspect_platform(settings: Settings) -> dict:
    services = {
        "database": _database_status(settings.database_path),
        "redis": _redis_status(settings.redis_url),
        "ollama": _ollama_status(settings),
    }
    core_ready = services["database"]["status"] == "ok" and services["redis"]["status"] in {"ok", "disabled"}
    if not core_ready:
        status = "unavailable"
    elif services["ollama"]["status"] not in {"ok", "disabled"}:
        status = "attention_required"
    else:
        status = "ready"
    return {"status": status, "services": services}


def _database_status(target: str) -> dict:
    try:
        with database_engine(target).connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        return {"status": "error", "message": f"数据库连接失败：{exc}"}
    return {"status": "ok", "message": "数据库连接正常。"}


def _redis_status(url: str) -> dict:
    if not url:
        return {"status": "disabled", "message": "未启用 Redis，任务将在 API 进程内执行。"}
    try:
        from redis import Redis

        Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2).ping()
    except Exception as exc:
        return {"status": "error", "message": f"Redis 连接失败：{exc}"}
    return {"status": "ok", "message": "Redis 队列连接正常。"}


def _ollama_status(settings: Settings) -> dict:
    if settings.notes_backend != "ollama":
        return {"status": "disabled", "message": "当前笔记引擎不需要 Ollama。"}
    try:
        models = list_ollama_models(settings.ollama_url, timeout_seconds=2)
    except RuntimeError as exc:
        return {"status": "error", "message": str(exc), "model": settings.ollama_model}

    installed = {model.name for model in models}
    selected = settings.ollama_model
    has_selected = selected in installed
    if ":" not in selected:
        has_selected = has_selected or f"{selected}:latest" in installed
    if not has_selected:
        return {
            "status": "model_missing",
            "message": f"Ollama 已启动，但尚未安装默认模型 {selected}。",
            "model": selected,
            "installed_models": sorted(installed),
        }
    return {
        "status": "ok",
        "message": f"Ollama 与默认模型 {selected} 已就绪。",
        "model": selected,
        "installed_models": sorted(installed),
    }
