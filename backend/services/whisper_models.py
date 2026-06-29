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
        name="ggml-large-v3-turbo.bin",
        label="大型 v3 Turbo 模型",
        size="1.6GB",
        path="models/ggml-large-v3-turbo.bin",
        url=f"{BASE_URL}/ggml-large-v3-turbo.bin",
        notes="本地质量与速度的最佳平衡，推荐用于正式笔记。",
        recommended=True,
    ),
]


def recommended_whisper_models() -> list[dict]:
    installed = installed_model_paths()
    return [
        {
            **asdict(option),
            "installed": _resolve_model_path(option.path) in installed,
        }
        for option in RECOMMENDED_WHISPER_MODELS
    ]


def installed_model_paths() -> set[Path]:
    if not MODEL_DIR.exists():
        return set()
    return {path.resolve() for path in MODEL_DIR.glob("ggml-*.bin") if path.is_file()}


def list_installed_whisper_models() -> list[str]:
    return [str(path.relative_to(PROJECT_ROOT)) for path in sorted(installed_model_paths())]


def download_whisper_model(model_name: str) -> dict:
    option = _find_model(model_name)
    target = _resolve_model_path(option.path)
    target.parent.mkdir(parents=True, exist_ok=True)

    if target.exists():
        return {"model": option.name, "path": str(target.relative_to(PROJECT_ROOT)), "downloaded": False}

    tmp_path = target.with_suffix(target.suffix + ".part")
    try:
        urllib.request.urlretrieve(option.url, tmp_path)
        shutil.move(str(tmp_path), target)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return {"model": option.name, "path": str(target.relative_to(PROJECT_ROOT)), "downloaded": True}


def _find_model(model_name: str) -> WhisperModelOption:
    for option in RECOMMENDED_WHISPER_MODELS:
        if model_name in {option.name, option.path}:
            return option
    raise ValueError(f"找不到 Whisper 模型：{model_name}")


def _resolve_model_path(path: str) -> Path:
    model_path = Path(path)
    if not model_path.is_absolute():
        model_path = PROJECT_ROOT / model_path
    return model_path.resolve()
