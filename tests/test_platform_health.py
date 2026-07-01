import unittest
from unittest.mock import patch

from backend.core.config import Settings
from backend.services.ollama_models import OllamaModel
from backend.services.platform_health import inspect_platform


class PlatformHealthTests(unittest.TestCase):
    @patch("backend.services.platform_health._ollama_status")
    @patch("backend.services.platform_health._redis_status")
    @patch("backend.services.platform_health._database_status")
    def test_reports_ready_when_all_services_are_available(self, database_status, redis_status, ollama_status):
        database_status.return_value = {"status": "ok"}
        redis_status.return_value = {"status": "ok"}
        ollama_status.return_value = {"status": "ok"}

        result = inspect_platform(Settings())

        self.assertEqual(result["status"], "ready")

    @patch("backend.services.platform_health._ollama_status")
    @patch("backend.services.platform_health._redis_status")
    @patch("backend.services.platform_health._database_status")
    def test_reports_attention_when_ollama_model_is_missing(self, database_status, redis_status, ollama_status):
        database_status.return_value = {"status": "ok"}
        redis_status.return_value = {"status": "disabled"}
        ollama_status.return_value = {"status": "model_missing"}

        result = inspect_platform(Settings())

        self.assertEqual(result["status"], "attention_required")

    @patch("backend.services.platform_health._ollama_status")
    @patch("backend.services.platform_health._redis_status")
    @patch("backend.services.platform_health._database_status")
    def test_reports_unavailable_when_database_fails(self, database_status, redis_status, ollama_status):
        database_status.return_value = {"status": "error"}
        redis_status.return_value = {"status": "ok"}
        ollama_status.return_value = {"status": "ok"}

        result = inspect_platform(Settings())

        self.assertEqual(result["status"], "unavailable")

    @patch("backend.services.platform_health.list_ollama_models")
    def test_does_not_accept_a_different_size_of_the_same_model(self, list_models):
        list_models.return_value = [
            OllamaModel("qwen2.5:14b", 1, "1 B", "", "qwen", "14B", "Q4")
        ]

        from backend.services.platform_health import _ollama_status

        result = _ollama_status(Settings(ollama_model="qwen2.5:32b"))

        self.assertEqual(result["status"], "model_missing")

    def test_skips_ollama_when_another_notes_backend_is_selected(self):
        from backend.services.platform_health import _ollama_status

        result = _ollama_status(Settings(notes_backend="extractive"))

        self.assertEqual(result["status"], "disabled")


if __name__ == "__main__":
    unittest.main()
