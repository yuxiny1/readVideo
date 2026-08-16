import io
import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from backend.services.ollama_client import OllamaClient


class OllamaClientTest(unittest.TestCase):
    @patch("backend.services.ollama_client.urllib.request.urlopen")
    def test_generate_hides_wire_format_from_callers(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = json.dumps({"response": "  生成内容  "}).encode("utf-8")

        result = OllamaClient("qwen", "http://ollama/api/generate", 30).generate("提示词")

        self.assertEqual(result, "生成内容")
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "qwen")
        self.assertEqual(payload["prompt"], "提示词")
        self.assertFalse(payload["stream"])
        self.assertFalse(payload["think"])
        self.assertEqual(payload["keep_alive"], "30m")
        urlopen.assert_called_once_with(request, timeout=30)

    @patch("backend.services.ollama_client.urllib.request.urlopen")
    def test_missing_model_is_translated_into_an_actionable_error(self, urlopen):
        error = urllib.error.HTTPError(
            "http://ollama/api/generate",
            404,
            "Not Found",
            {},
            io.BytesIO(json.dumps({"error": "model not found, try pull"}).encode("utf-8")),
        )
        self.addCleanup(error.close)
        urlopen.side_effect = error

        with self.assertRaisesRegex(RuntimeError, "ollama pull qwen"):
            OllamaClient("qwen", "http://ollama/api/generate", 30).generate("提示词")

    @patch("backend.services.ollama_client.time.sleep")
    @patch("backend.services.ollama_client.urllib.request.urlopen")
    def test_connection_errors_are_actionable(self, urlopen, sleep):
        urlopen.side_effect = urllib.error.URLError("connection refused")

        with self.assertRaisesRegex(RuntimeError, "无法连接 Ollama.*connection refused"):
            OllamaClient("qwen", "http://ollama", 30).generate("提示词")

        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(1)

    @patch("backend.services.ollama_client.time.sleep")
    @patch("backend.services.ollama_client.urllib.request.urlopen")
    def test_transient_connection_error_is_retried(self, urlopen, sleep):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            {"response": "重试成功"}
        ).encode("utf-8")
        urlopen.side_effect = [ConnectionResetError("connection reset"), response]

        result = OllamaClient("qwen", "http://ollama", 30).generate("提示词")

        self.assertEqual(result, "重试成功")
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(1)

    @patch("backend.services.ollama_client.time.sleep")
    @patch("backend.services.ollama_client.urllib.request.urlopen")
    def test_timeout_does_not_claim_the_model_is_missing(self, urlopen, sleep):
        urlopen.side_effect = TimeoutError("timed out")

        with self.assertRaises(RuntimeError) as raised:
            OllamaClient("qwen", "http://ollama", 900).generate("提示词")

        self.assertIn("单次等待 900 秒", str(raised.exception))
        self.assertNotIn("ollama pull", str(raised.exception))
        sleep.assert_called_once_with(1)

    @patch("backend.services.ollama_client.urllib.request.urlopen")
    def test_empty_response_is_reported(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = json.dumps({"response": "", "done_reason": "stop"}).encode(
            "utf-8"
        )

        with self.assertRaisesRegex(RuntimeError, "没有返回可用内容"):
            OllamaClient("qwen", "http://ollama", 30).generate("提示词")


if __name__ == "__main__":
    unittest.main()
