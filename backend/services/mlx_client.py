import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit


@dataclass(frozen=True)
class MlxServerStatus:
    models: list[str]


class MlxClient:
    def __init__(self, model: str, url: str, timeout_seconds: int):
        self._model = model
        self._url = url
        self._timeout_seconds = timeout_seconds

    def generate(self, prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self._model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 4096,
                "stream": False,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self._url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = _read_error(exc)
            raise RuntimeError(f"MLX 本地模型生成失败：{detail}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError(
                "无法连接 MLX 本地模型服务。请先确认模型已下载完成，再运行："
                f"~/mlx-env/bin/mlx_lm.server --model {self._model} --host 127.0.0.1 --port 8080"
            ) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("MLX 本地模型服务返回了无法解析的数据。") from exc

        content = _response_content(data)
        if not content:
            raise RuntimeError("MLX 本地模型没有返回可用内容。")
        return content


def inspect_mlx_server(url: str, timeout_seconds: int = 3) -> MlxServerStatus:
    request = urllib.request.Request(_models_url(url), method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"MLX 本地模型服务检查失败：{_read_error(exc)}") from exc
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError("MLX 本地模型服务未启动。") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("MLX 本地模型服务返回了无法解析的数据。") from exc

    models = [
        str(item.get("id") or "").strip()
        for item in data.get("data", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    return MlxServerStatus(models=models)


def _models_url(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, "/v1/models", "", ""))


def _response_content(data: object) -> str:
    if not isinstance(data, dict):
        return ""
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return ""
    message = choices[0].get("message")
    if not isinstance(message, dict):
        return ""
    return str(message.get("content") or "").strip()


def _read_error(exc: urllib.error.HTTPError) -> str:
    try:
        data = json.loads(exc.read().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return str(exc.reason or "未知网络错误")
    if not isinstance(data, dict):
        return str(exc.reason or "未知网络错误")
    detail = data.get("detail") or data.get("error") or exc.reason or "未知网络错误"
    if isinstance(detail, dict):
        return str(detail.get("message") or detail)
    return str(detail)
