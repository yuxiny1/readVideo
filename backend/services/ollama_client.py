import json
import logging
import time
import urllib.error
import urllib.request


logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(
        self,
        model: str,
        url: str,
        timeout_seconds: int,
        retry_attempts: int = 2,
        keep_alive: str = "30m",
    ):
        self._model = model
        self._url = url
        self._timeout_seconds = timeout_seconds
        self._retry_attempts = max(1, retry_attempts)
        self._keep_alive = keep_alive

    def generate(self, prompt: str) -> str:
        payload = json.dumps(
            {
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "keep_alive": self._keep_alive,
                "options": {"temperature": 0.2},
            }
        ).encode("utf-8")
        data = self._send_with_retry(payload)
        return self._response_text(data)

    def _send_with_retry(self, payload: bytes) -> object:
        for attempt in range(1, self._retry_attempts + 1):
            request = urllib.request.Request(
                self._url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self._timeout_seconds) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                detail = self._read_error(exc)
                if exc.code >= 500 and self._should_retry(attempt):
                    self._wait_before_retry(attempt, f"HTTP {exc.code}: {detail}")
                    continue
                if "not found" in detail.lower() or "pull" in detail.lower():
                    raise RuntimeError(
                        f'Ollama 模型“{self._model}”尚未安装，请运行：ollama pull {self._model}'
                    ) from exc
                raise RuntimeError(f"Ollama 总结失败：{detail}") from exc
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                if self._should_retry(attempt):
                    self._wait_before_retry(attempt, str(exc))
                    continue
                raise self._transport_error(exc) from exc
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise RuntimeError("Ollama 返回了无法解析的数据，请查看后端日志后重试。") from exc

        raise RuntimeError("Ollama 总结失败，重试次数已用尽。")

    def _should_retry(self, attempt: int) -> bool:
        return attempt < self._retry_attempts

    def _wait_before_retry(self, attempt: int, detail: str) -> None:
        logger.warning(
            "Ollama 请求失败，准备重试（第 %s/%s 次，模型=%s）：%s",
            attempt,
            self._retry_attempts,
            self._model,
            detail,
        )
        time.sleep(min(attempt, 2))

    def _transport_error(self, exc: BaseException) -> RuntimeError:
        reason = getattr(exc, "reason", exc)
        if isinstance(exc, TimeoutError) or isinstance(reason, TimeoutError):
            return RuntimeError(
                f'Ollama 总结超时（单次等待 {self._timeout_seconds} 秒，模型“{self._model}”）。'
                "模型已安装时无需重新下载，请直接重试；详细原因已写入后端日志。"
            )
        return RuntimeError(
            f"无法连接 Ollama（{self._url}）：{reason}。请确认 Ollama 服务正在运行后重试。"
        )

    @staticmethod
    def _response_text(data: object) -> str:
        if not isinstance(data, dict):
            raise RuntimeError("Ollama 返回的数据格式不正确，请查看后端日志后重试。")
        content = str(data.get("response") or "").strip()
        if content:
            return content
        if str(data.get("thinking") or "").strip():
            raise RuntimeError("Ollama 只返回了思考过程，没有生成最终笔记，请重试。")
        reason = str(data.get("done_reason") or "未知原因")
        raise RuntimeError(f"Ollama 没有返回可用内容（结束原因：{reason}）。")

    @staticmethod
    def _read_error(exc: urllib.error.HTTPError) -> str:
        try:
            data = json.loads(exc.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return exc.reason or "未知的 Ollama 网络错误"
        return str(data.get("error") or exc.reason or "未知的 Ollama 网络错误")
