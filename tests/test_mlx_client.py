import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from backend.services.mlx_client import MlxClient, inspect_mlx_server


class MlxClientTest(unittest.TestCase):
    @patch("backend.services.mlx_client.urllib.request.urlopen")
    def test_generate_uses_openai_compatible_chat_completions(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "  生成内容  "}}]}
        ).encode("utf-8")

        result = MlxClient("mlx/model", "http://127.0.0.1:8080/v1/chat/completions", 30).generate("提示词")

        self.assertEqual(result, "生成内容")
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["model"], "mlx/model")
        self.assertEqual(payload["messages"], [{"role": "user", "content": "提示词"}])
        self.assertEqual(payload["max_tokens"], 4096)
        self.assertFalse(payload["stream"])

    @patch("backend.services.mlx_client.urllib.request.urlopen")
    def test_inspect_lists_models_available_in_the_server_cache(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = json.dumps(
            {"data": [{"id": "mlx-community/Qwen2.5-72B-Instruct-3bit"}]}
        ).encode("utf-8")

        result = inspect_mlx_server("http://127.0.0.1:8080/v1/chat/completions")

        self.assertEqual(result.models, ["mlx-community/Qwen2.5-72B-Instruct-3bit"])
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:8080/v1/models")

    @patch("backend.services.mlx_client.urllib.request.urlopen")
    def test_connection_error_explains_how_to_start_the_selected_model(self, urlopen):
        urlopen.side_effect = urllib.error.URLError("connection refused")

        with self.assertRaisesRegex(RuntimeError, "mlx_lm.server --model mlx/model"):
            MlxClient("mlx/model", "http://127.0.0.1:8080/v1/chat/completions", 30).generate("提示词")

    @patch("backend.services.mlx_client.urllib.request.urlopen")
    def test_http_error_is_translated_without_losing_server_detail(self, urlopen):
        error = urllib.error.HTTPError(
            "http://127.0.0.1:8080/v1/chat/completions",
            400,
            "Bad Request",
            {},
            io.BytesIO(json.dumps({"detail": "model is not loaded"}).encode("utf-8")),
        )
        self.addCleanup(error.close)
        urlopen.side_effect = error

        with self.assertRaisesRegex(RuntimeError, "model is not loaded"):
            MlxClient("mlx/model", "http://127.0.0.1:8080/v1/chat/completions", 30).generate("提示词")


if __name__ == "__main__":
    unittest.main()
