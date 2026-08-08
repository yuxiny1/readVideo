import json
import urllib.error
import urllib.request


class OllamaClient:
    def __init__(self, model: str, url: str, timeout_seconds: int):
        self._model = model
        self._url = url
        self._timeout_seconds = timeout_seconds

    def generate(self, prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2},
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
            detail = self._read_error(exc)
            if "not found" in detail.lower() or "pull" in detail.lower():
                raise RuntimeError(
                    f'Ollama 模型“{self._model}”尚未安装，请运行：ollama pull {self._model}'
                ) from exc
            raise RuntimeError(f"Ollama 总结失败：{detail}") from exc
        except (urllib.error.URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(
                f"Ollama 总结失败。请确认 Ollama 正在 {self._url} 运行，"
                f"并已安装模型：ollama pull {self._model}"
            ) from exc
        return str(data.get("response", "")).strip()

    @staticmethod
    def _read_error(exc: urllib.error.HTTPError) -> str:
        try:
            data = json.loads(exc.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return exc.reason or "未知的 Ollama 网络错误"
        return str(data.get("error") or exc.reason or "未知的 Ollama 网络错误")
