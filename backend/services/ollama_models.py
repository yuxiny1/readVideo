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
    OllamaModelOption("qwen2.5:3b", "Qwen2.5 3B", "1.9GB", "轻量备用模型，速度快，但笔记质量较弱。"),
    OllamaModelOption("qwen2.5:7b", "Qwen2.5 7B", "4.7GB", "适合普通电脑的中英文通用总结模型。"),
    OllamaModelOption("qwen2.5:14b", "Qwen2.5 14B", "9.0GB", "内存充足时可获得更好的结构和推理能力。"),
    OllamaModelOption("qwen2.5:32b", "Qwen2.5 32B", "20GB", "安装后默认使用的高质量本地笔记模型。"),
    OllamaModelOption("qwen3:8b", "Qwen3 8B", "5.2GB", "较新的 Qwen 系列，速度与质量较均衡。"),
    OllamaModelOption("qwen3:14b", "Qwen3 14B", "9.3GB", "硬件开销适中，可生成质量更高的本地总结。"),
    OllamaModelOption("qwen3:30b", "Qwen3 30B", "19GB", "适合更强推理和内容组织的大型本地模型。"),
    OllamaModelOption("llama3.1:8b", "Llama 3.1 8B", "4.9GB", "多语言能力较强的通用模型。"),
)


def recommended_models() -> list[dict]:
    return [asdict(model) for model in RECOMMENDED_OLLAMA_MODELS]


def validate_model_name(model: str) -> str:
    cleaned = model.strip()
    if not cleaned or not MODEL_NAME_PATTERN.fullmatch(cleaned):
        raise RuntimeError("Ollama 模型名称包含无效字符。")
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
        raise RuntimeError("尚未安装 Ollama 命令行工具，或该工具不在 PATH 中。") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"下载模型 {model_name} 超时。") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise RuntimeError(f"无法下载模型 {model_name}：{detail}") from exc

    return result.stdout.strip() or f"模型 {model_name} 已安装。"


def list_ollama_models(generate_url: str, timeout_seconds: int = 5) -> list[OllamaModel]:
    request = urllib.request.Request(_ollama_api_url(generate_url, "/api/tags"), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法连接位于 {_ollama_base_url(generate_url)} 的 Ollama 服务。") from exc

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
        raise RuntimeError(_ollama_http_error(exc, f"无法下载 Ollama 模型 {model}。")) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法下载 Ollama 模型 {model}。") from exc


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
        raise RuntimeError(f"Ollama 地址无效：{generate_url}")
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
