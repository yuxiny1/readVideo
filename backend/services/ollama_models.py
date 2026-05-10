import re
import subprocess
from dataclasses import asdict, dataclass


MODEL_NAME_PATTERN = re.compile(r"^[A-Za-z0-9._/-]+(?::[A-Za-z0-9._-]+)?$")


@dataclass(frozen=True)
class OllamaModelOption:
    name: str
    label: str
    size: str
    notes: str


RECOMMENDED_OLLAMA_MODELS = (
    OllamaModelOption("qwen2.5:3b", "Qwen2.5 3B", "1.9GB", "Current lightweight default; fast, but weaker notes."),
    OllamaModelOption("qwen2.5:7b", "Qwen2.5 7B", "4.7GB", "Good general Chinese/English summaries on typical laptops."),
    OllamaModelOption("qwen2.5:14b", "Qwen2.5 14B", "9.0GB", "Better structure and reasoning if you have enough memory."),
    OllamaModelOption("qwen2.5:32b", "Qwen2.5 32B", "20GB", "Much stronger, but needs a powerful machine."),
    OllamaModelOption("qwen3:8b", "Qwen3 8B", "5.2GB", "Newer Qwen family; strong balanced option."),
    OllamaModelOption("qwen3:14b", "Qwen3 14B", "9.3GB", "Higher quality local summaries with moderate hardware cost."),
    OllamaModelOption("qwen3:30b", "Qwen3 30B", "19GB", "Large local model for stronger reasoning and organization."),
    OllamaModelOption("llama3.1:8b", "Llama 3.1 8B", "4.9GB", "Strong multilingual general model."),
)


def recommended_models() -> list[dict]:
    return [asdict(model) for model in RECOMMENDED_OLLAMA_MODELS]


def validate_model_name(model: str) -> str:
    cleaned = model.strip()
    if not cleaned or not MODEL_NAME_PATTERN.fullmatch(cleaned):
        raise RuntimeError("Ollama model name contains invalid characters.")
    return cleaned


def list_installed_models() -> list[str]:
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            check=True,
            text=True,
            timeout=20,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return []

    names = []
    for line in result.stdout.splitlines()[1:]:
        columns = line.split()
        if columns:
            names.append(columns[0])
    return names


def pull_model(model: str) -> str:
    model_name = validate_model_name(model)
    try:
        result = subprocess.run(
            ["ollama", "pull", model_name],
            capture_output=True,
            check=True,
            text=True,
            timeout=1800,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("Ollama CLI is not installed or not on PATH.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"Timed out while pulling {model_name}.") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise RuntimeError(f"Could not pull {model_name}: {detail}") from exc

    return result.stdout.strip() or f"Installed {model_name}."
