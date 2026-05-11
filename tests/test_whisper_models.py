import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services import whisper_models


class WhisperModelsTest(unittest.TestCase):
    def test_recommended_models_marks_installed_files(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.object(whisper_models, "PROJECT_ROOT", Path(tmpdir)):
            model_dir = Path(tmpdir) / "models"
            model_dir.mkdir()
            model_path = model_dir / "ggml-small.bin"
            model_path.write_text("fake", encoding="utf-8")
            with patch.object(whisper_models, "MODEL_DIR", model_dir):
                models = whisper_models.recommended_whisper_models()

        small = next(item for item in models if item["name"] == "ggml-small.bin")
        self.assertTrue(small["installed"])

    def test_download_whisper_model_rejects_unknown_model(self):
        with self.assertRaisesRegex(ValueError, "Unknown"):
            whisper_models.download_whisper_model("not-a-model.bin")

    def test_download_whisper_model_writes_target_once(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.object(whisper_models, "PROJECT_ROOT", Path(tmpdir).resolve()):
            target = Path(tmpdir).resolve() / "models" / "ggml-medium.bin"

            def fake_urlretrieve(url, tmp_path):
                Path(tmp_path).write_text(f"downloaded from {url}", encoding="utf-8")

            with patch.object(whisper_models.urllib.request, "urlretrieve", fake_urlretrieve):
                first = whisper_models.download_whisper_model("ggml-medium.bin")
                second = whisper_models.download_whisper_model("ggml-medium.bin")
                target_exists = target.exists()

        self.assertTrue(first["downloaded"])
        self.assertFalse(second["downloaded"])
        self.assertEqual(first["path"], "models/ggml-medium.bin")
        self.assertTrue(target_exists)


if __name__ == "__main__":
    unittest.main()
