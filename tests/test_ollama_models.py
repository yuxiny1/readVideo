import subprocess
import unittest
from unittest.mock import patch

from backend.services.ollama_models import list_installed_models, pull_model, recommended_models


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
        with self.assertRaisesRegex(RuntimeError, "invalid"):
            pull_model("bad model; rm -rf /")


if __name__ == "__main__":
    unittest.main()
