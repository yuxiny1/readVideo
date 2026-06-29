import subprocess
import unittest
from unittest.mock import patch

from backend.services.ollama_models import (
    list_installed_models,
    list_ollama_models,
    pull_model,
    pull_ollama_model,
    recommended_models,
)


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.payload


class OllamaModelsTest(unittest.TestCase):
    def test_recommended_models_include_larger_options(self):
        names = {model["name"] for model in recommended_models()}
        self.assertIn("qwen2.5:14b", names)
        self.assertIn("qwen3:30b", names)

    def test_list_installed_models_parses_ollama_output(self):
        result = subprocess.CompletedProcess(
            args=["ollama", "list"],
            returncode=0,
            stdout="NAME ID SIZE MODIFIED\nqwen2.5:3b abc 1.9GB now\nqwen3:14b def 9.3GB now\n",
        )
        with patch("backend.services.ollama_models.subprocess.run", return_value=result):
            self.assertEqual(list_installed_models(), ["qwen2.5:3b", "qwen3:14b"])

    def test_pull_model_validates_model_name(self):
        with self.assertRaisesRegex(RuntimeError, "无效字符"):
            pull_model("bad model; rm -rf /")

    def test_list_ollama_models_parses_api_response(self):
        payload = (
            b'{"models": [{"name": "qwen3:14b", "size": 998877, '
            b'"modified_at": "2026-05-18T12:00:00Z", '
            b'"details": {"family": "qwen3", "parameter_size": "14B", "quantization_level": "Q4_K_M"}}]}'
        )
        with patch("backend.services.ollama_models.urllib.request.urlopen", return_value=FakeResponse(payload)):
            models = list_ollama_models("http://127.0.0.1:11434/api/generate")

        self.assertEqual(models[0].name, "qwen3:14b")
        self.assertEqual(models[0].family, "qwen3")
        self.assertEqual(models[0].size_label, "975.5 KB")

    def test_pull_ollama_model_parses_non_streaming_response(self):
        with patch(
            "backend.services.ollama_models.urllib.request.urlopen",
            return_value=FakeResponse(b'{"status": "success"}'),
        ):
            result = pull_ollama_model("qwen3:14b", "http://127.0.0.1:11434/api/generate")

        self.assertEqual(result["status"], "success")

    def test_list_installed_models_returns_empty_when_cli_unavailable(self):
        with patch("backend.services.ollama_models.subprocess.run", side_effect=FileNotFoundError):
            self.assertEqual(list_installed_models(), [])


if __name__ == "__main__":
    unittest.main()
