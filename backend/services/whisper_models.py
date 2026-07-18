import shutil
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = PROJECT_ROOT / "models"
BASE_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main"


@dataclass(frozen=True)
class WhisperModelOption:
    name: str
    label: str
    size: str
    path: str
    url: str
    notes: str
    recommended: bool = False


RECOMMENDED_WHISPER_MODELS = [
    WhisperModelOption(
        name="ggml-base.bin",
        label="基础模型",
        size="141MB",
        path="models/ggml-base.bin",
        url=f"{BASE_URL}/ggml-base.bin",
        notes="适合快速测试；处理噪声或混合语言视频时准确度较低。",
    ),
    WhisperModelOption(
        name="ggml-small.bin",
        label="小型模型",
        size="465MB",
        path="models/ggml-small.bin",
        url=f"{BASE_URL}/ggml-small.bin",
        notes="速度快，但处理噪声、英语或混合语言语音时更容易重复或误识别。",
    ),
    WhisperModelOption(
        name="ggml-medium.bin",
        label="中型模型",
        size="1.5GB",
        path="models/ggml-medium.bin",
        url=f"{BASE_URL}/ggml-medium.bin",
        notes="处理网络视频、口音和混合语言时准确度更高。",
    ),
    WhisperModelOption(
        name="ggml-large-v3.bin",
        label="大型 v3 高精度模型",
        size="3.1GB",
        path="models/ggml-large-v3.bin",
        url=f"{BASE_URL}/ggml-large-v3.bin",
        notes="本地转录质量优先，适合课程、访谈和噪声较多的视频；速度比 Turbo 慢。",
        recommended=True,
    ),
    WhisperModelOption(
        name="ggml-large-v3-turbo.bin",
        label="大型 v3 Turbo 模型",
        size="1.6GB",
        path="models/ggml-large-v3-turbo.bin",
        url=f"{BASE_URL}/ggml-large-v3-turbo.bin",
        notes="质量与速度的平衡方案；如果高精度模型太慢，可以切回这个模型。",
    ),
]


def recommended_whisper_models(configured_model_path: str | None = None) -> list[dict]:
    installed = installed_model_paths(configured_model_path)
    models = []
    for option in RECOMMENDED_WHISPER_MODELS:
        resolved_path = _resolve_model_path(option.path, configured_model_path)
        models.append({
            **asdict(option),
            "path": _display_model_path(resolved_path),
            "installed": resolved_path in installed,
        })
    return models


def installed_model_paths(configured_model_path: str | None = None) -> set[Path]:
    model_dir = _model_directory(configured_model_path)
    if not model_dir.exists():
        return set()
    return {path.resolve() for path in model_dir.glob("ggml-*.bin") if path.is_file()}


def list_installed_whisper_models(configured_model_path: str | None = None) -> list[str]:
    return [_display_model_path(path) for path in sorted(installed_model_paths(configured_model_path))]


def download_whisper_model(model_name: str, configured_model_path: str | None = None) -> dict:
    option = _find_model(model_name)
    target = _resolve_model_path(option.path, configured_model_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        return {"model": option.name, "path": _display_model_path(target), "downloaded": False}

    tmp_path = target.with_suffix(target.suffix + ".part")
    try:
        urllib.request.urlretrieve(option.url, tmp_path)
        shutil.move(str(tmp_path), target)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return {"model": option.name, "path": _display_model_path(target), "downloaded": True}


def _find_model(model_name: str) -> WhisperModelOption:
    for option in RECOMMENDED_WHISPER_MODELS:
        if model_name in {option.name, option.path}:
            return option
    raise ValueError(f"找不到 Whisper 模型：{model_name}")


def _resolve_model_path(path: str, configured_model_path: str | None = None) -> Path:
    if configured_model_path:
        return (_model_directory(configured_model_path) / Path(path).name).resolve()
    model_path = Path(path)
    if not model_path.is_absolute():
        model_path = PROJECT_ROOT / model_path
    return model_path.resolve()


def _model_directory(configured_model_path: str | None) -> Path:
    if not configured_model_path:
        return MODEL_DIR.resolve()
    configured = Path(configured_model_path).expanduser()
    if not configured.is_absolute():
        configured = PROJECT_ROOT / configured
    return configured.resolve().parent


def _display_model_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        return str(path)
