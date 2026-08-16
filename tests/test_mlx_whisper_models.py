import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from backend.services import mlx_whisper_models


class MlxWhisperModelsTest(unittest.TestCase):
    def test_catalog_marks_complete_hugging_face_snapshot_as_installed(self):
        with tempfile.TemporaryDirectory() as tmpdir, patch.dict(
            "os.environ", {"HF_HOME": tmpdir}, clear=False
        ):
            snapshot = (
                Path(tmpdir)
                / "hub/models--mlx-community--whisper-large-v3-mlx/snapshots/revision"
            )
            snapshot.mkdir(parents=True)
            (snapshot / "config.json").write_text("{}", encoding="utf-8")
            (snapshot / "weights.npz").write_bytes(b"weights")

            models = mlx_whisper_models.recommended_mlx_whisper_models()

        large = next(model for model in models if model["recommended"])
        self.assertTrue(large["installed"])
        self.assertEqual(large["engine"], "mlx")

    def test_runtime_reports_missing_python_and_successful_import(self):
        missing = mlx_whisper_models.inspect_mlx_whisper_runtime("/missing/python")
        self.assertFalse(missing["available"])

        completed = CompletedProcess(args=[], returncode=0, stdout=b"", stderr=b"")
        with patch.object(mlx_whisper_models, "_resolve_python_executable", return_value="/mlx/python"), patch.object(
            mlx_whisper_models.subprocess, "run", return_value=completed
        ):
            available = mlx_whisper_models.inspect_mlx_whisper_runtime("python")

        self.assertTrue(available["available"])
        self.assertEqual(available["python"], "/mlx/python")

    def test_download_uses_hugging_face_once(self):
        model = mlx_whisper_models.DEFAULT_MLX_WHISPER_MODEL
        with patch.object(
            mlx_whisper_models, "inspect_mlx_whisper_runtime", return_value={
                "available": True,
                "python": "/mlx/python",
                "error": "",
            }
        ), patch.object(
            mlx_whisper_models,
            "mlx_whisper_model_installed",
            side_effect=[False, True, True],
        ), patch.object(
            mlx_whisper_models.subprocess,
            "run",
            return_value=CompletedProcess(args=[], returncode=0, stdout=b"", stderr=b""),
        ) as run:
            first = mlx_whisper_models.download_mlx_whisper_model(model, "python")
            second = mlx_whisper_models.download_mlx_whisper_model(model, "python")

        self.assertTrue(first["downloaded"])
        self.assertFalse(second["downloaded"])
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
