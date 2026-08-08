import io
import json
import unittest
import urllib.error
from unittest.mock import patch

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

    @patch("backend.services.ollama_client.urllib.request.urlopen")
    def test_connection_errors_do_not_leak_transport_details(self, urlopen):
        urlopen.side_effect = urllib.error.URLError("connection refused")

        with self.assertRaisesRegex(RuntimeError, "请确认 Ollama 正在 http://ollama"):
            OllamaClient("qwen", "http://ollama", 30).generate("提示词")


if __name__ == "__main__":
    unittest.main()
