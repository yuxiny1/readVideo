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


RECOMMENDED_WHISPER_MODELS = [
    WhisperModelOption(
        name="ggml-base.bin",
        label="Base",
        size="141MB",
        path="models/ggml-base.bin",
        url=f"{BASE_URL}/ggml-base.bin",
        notes="Fast smoke tests. Lower accuracy on noisy or mixed-language videos.",
    ),
    WhisperModelOption(
        name="ggml-small.bin",
        label="Small",
        size="465MB",
        path="models/ggml-small.bin",
        url=f"{BASE_URL}/ggml-small.bin",
        notes="Good default speed, but can hallucinate on English or mixed-language speech.",
    ),
    WhisperModelOption(
        name="ggml-medium.bin",
        label="Medium",
        size="1.5GB",
        path="models/ggml-medium.bin",
        url=f"{BASE_URL}/ggml-medium.bin",
        notes="Better accuracy for YouTube speech, accents, and mixed languages.",
    ),
    WhisperModelOption(
        name="ggml-large-v3-turbo.bin",
        label="Large v3 Turbo",
        size="1.6GB",
        path="models/ggml-large-v3-turbo.bin",
        url=f"{BASE_URL}/ggml-large-v3-turbo.bin",
        notes="Best local quality/speed tradeoff here; recommended for final notes.",
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
    raise ValueError(f"Unknown Whisper model: {model_name}")


def _resolve_model_path(path: str) -> Path:
    model_path = Path(path)
    if not model_path.is_absolute():
        model_path = PROJECT_ROOT / model_path
    return model_path.resolve()
