import json
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class OllamaModel:
    name: str
    size: int
    size_label: str
    modified_at: str
    family: str
    parameter_size: str
    quantization_level: str


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


def list_ollama_models(generate_url: str, timeout_seconds: int = 5) -> list[OllamaModel]:
    request = urllib.request.Request(_ollama_api_url(generate_url, "/api/tags"), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not reach Ollama at {_ollama_base_url(generate_url)}.") from exc

    models = data.get("models") or []
    return [_model_from_payload(model) for model in models]


def pull_ollama_model(model: str, generate_url: str, timeout_seconds: int = 600) -> dict[str, Any]:
    payload = json.dumps({"name": model, "stream": False}).encode("utf-8")
    request = urllib.request.Request(
        _ollama_api_url(generate_url, "/api/pull"),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(_ollama_http_error(exc, f"Could not pull Ollama model {model}.")) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not pull Ollama model {model}.") from exc


def _model_from_payload(payload: dict[str, Any]) -> OllamaModel:
    details = payload.get("details") or {}
    name = str(payload.get("name") or payload.get("model") or "")
    size = int(payload.get("size") or 0)
    return OllamaModel(
        name=name,
        size=size,
        size_label=_format_bytes(size),
        modified_at=str(payload.get("modified_at") or ""),
        family=str(details.get("family") or ""),
        parameter_size=str(details.get("parameter_size") or ""),
        quantization_level=str(details.get("quantization_level") or ""),
    )


def _ollama_api_url(generate_url: str, path: str) -> str:
    parsed = urllib.parse.urlparse(generate_url)
    if not parsed.scheme or not parsed.netloc:
        raise RuntimeError(f"Invalid Ollama URL: {generate_url}")
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, path, "", "", ""))


def _ollama_base_url(generate_url: str) -> str:
    parsed = urllib.parse.urlparse(generate_url)
    if not parsed.scheme or not parsed.netloc:
        return generate_url
    return urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


def _ollama_http_error(exc: urllib.error.HTTPError, fallback: str) -> str:
    try:
        data = json.loads(exc.read().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return fallback
    return str(data.get("error") or fallback)


def _format_bytes(size: int) -> str:
    if size <= 0:
        return "-"
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
