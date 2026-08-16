import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from backend.services.media_audio import decode_process_output


DEFAULT_MLX_WHISPER_MODEL = "mlx-community/whisper-large-v3-mlx"


@dataclass(frozen=True)
class MlxWhisperModelOption:
    name: str
    label: str
    size: str
    notes: str
    recommended: bool = False


MLX_WHISPER_MODELS = [
    MlxWhisperModelOption(
        name=DEFAULT_MLX_WHISPER_MODEL,
        label="MLX 大型 v3 高精度模型",
        size="3.1GB",
        notes="完整大型 v3 权重，优先保证中文、课程和中英混合内容的准确度。",
        recommended=True,
    ),
    MlxWhisperModelOption(
        name="mlx-community/whisper-large-v3-turbo",
        label="MLX 大型 v3 Turbo 模型",
        size="1.6GB",
        notes="速度更快、占用更低，准确度略低于完整大型 v3。",
    ),
]


def recommended_mlx_whisper_models() -> list[dict]:
    return [
        {
            **asdict(option),
            "path": option.name,
            "url": f"https://huggingface.co/{option.name}",
            "engine": "mlx",
            "installed": mlx_whisper_model_installed(option.name),
        }
        for option in MLX_WHISPER_MODELS
    ]


def list_installed_mlx_whisper_models() -> list[str]:
    return [option.name for option in MLX_WHISPER_MODELS if mlx_whisper_model_installed(option.name)]


def mlx_whisper_model_installed(model_name: str) -> bool:
    snapshots = _model_cache_dir(model_name) / "snapshots"
    if not snapshots.is_dir():
        return False
    return any(_complete_snapshot(path) for path in snapshots.iterdir() if path.is_dir())


def inspect_mlx_whisper_runtime(python_executable: str) -> dict:
    resolved = _resolve_python_executable(python_executable)
    if resolved is None:
        return {
            "available": False,
            "python": str(Path(python_executable).expanduser()),
            "error": "未找到 MLX Python 环境，请先运行 npm run mlx:whisper:install。",
        }
    try:
        result = subprocess.run(
            [resolved, "-c", "import mlx_whisper"],
            cwd=Path.home(),
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "available": False,
            "python": resolved,
            "error": f"无法检查 MLX Whisper 运行环境：{exc}",
        }
    if result.returncode != 0:
        detail = decode_process_output(result.stderr or result.stdout).strip()
        return {
            "available": False,
            "python": resolved,
            "error": detail or "MLX Python 环境中尚未安装 mlx-whisper。",
        }
    return {"available": True, "python": resolved, "error": ""}


def download_mlx_whisper_model(model_name: str, python_executable: str) -> dict:
    option = _find_model(model_name)
    runtime = inspect_mlx_whisper_runtime(python_executable)
    if not runtime["available"]:
        raise RuntimeError(runtime["error"])
    if mlx_whisper_model_installed(option.name):
        return {"model": option.name, "path": option.name, "downloaded": False}

    command = [
        runtime["python"],
        "-c",
        "from huggingface_hub import snapshot_download; import sys; snapshot_download(sys.argv[1])",
        option.name,
    ]
    result = subprocess.run(command, cwd=Path.home(), capture_output=True, check=False)
    if result.returncode != 0:
        detail = decode_process_output(result.stderr or result.stdout).strip()
        raise RuntimeError(f"MLX Whisper 模型下载失败：{detail or '未知错误'}")
    if not mlx_whisper_model_installed(option.name):
        raise RuntimeError("模型下载命令已结束，但 Hugging Face 缓存中没有找到完整权重。")
    return {"model": option.name, "path": option.name, "downloaded": True}


def _find_model(model_name: str) -> MlxWhisperModelOption:
    for option in MLX_WHISPER_MODELS:
        if model_name == option.name:
            return option
    raise ValueError(f"找不到 MLX Whisper 模型：{model_name}")


def _model_cache_dir(model_name: str) -> Path:
    cache_root = os.getenv("HF_HUB_CACHE")
    if cache_root:
        hub = Path(cache_root).expanduser()
    else:
        hf_home = Path(os.getenv("HF_HOME", "~/.cache/huggingface")).expanduser()
        hub = hf_home / "hub"
    return hub / f"models--{model_name.replace('/', '--')}"


def _complete_snapshot(snapshot: Path) -> bool:
    has_config = (snapshot / "config.json").is_file()
    has_weights = any((snapshot / name).is_file() for name in (
        "weights.npz",
        "weights.safetensors",
        "model.safetensors",
    ))
    return has_config and has_weights


def _resolve_python_executable(python_executable: str) -> str | None:
    expanded = Path(python_executable).expanduser()
    if expanded.is_file():
        return str(expanded)
    return shutil.which(python_executable)
