import unittest
from unittest.mock import patch

from backend.core.config import Settings
from backend.services.processing_settings import resolve_processing_plan


class ProcessingSettingsTest(unittest.TestCase):
    def test_defaults_are_resolved_into_one_processing_plan(self):
        settings = Settings(
            notes_dir="default-notes",
            notes_backend="ollama",
            note_style="detailed",
            ollama_model="qwen-default",
            transcription_backend="local",
            local_whisper_model="models/default.bin",
            local_whisper_language="auto",
        )

        plan = resolve_processing_plan(settings)

        self.assertEqual(plan.notes_dir, "default-notes")
        self.assertEqual(plan.notes_backend, "ollama")
        self.assertEqual(plan.note_style, "detailed")
        self.assertEqual(plan.ollama_model, "qwen-default")
        self.assertEqual(
            plan.task_metadata(delete_video_after_completion=True),
            {
                "notes_backend": "ollama",
                "note_style": "detailed",
                "ollama_model": "qwen-default",
                "transcription_backend": "local",
                "transcription_model": None,
                "local_whisper_model": "models/default.bin",
                "local_whisper_language": "auto",
                "delete_video_after_completion": True,
            },
        )

    def test_request_values_override_defaults_without_mutating_settings(self):
        settings = Settings(
            notes_backend="extractive",
            note_style="detailed",
            transcription_backend="local",
            local_whisper_prompt="default prompt",
        )

        plan = resolve_processing_plan(
            settings,
            notes_dir="custom-notes",
            notes_backend="ollama",
            note_style="commercial",
            ollama_model="qwen-custom",
            transcription_model="custom-transcriber",
            transcription_prompt="  custom prompt  ",
            local_whisper_model="models/custom.bin",
            local_whisper_language="zh",
        )

        self.assertEqual(plan.notes_dir, "custom-notes")
        self.assertEqual(plan.notes_backend, "ollama")
        self.assertEqual(plan.note_style, "commercial")
        self.assertEqual(plan.ollama_model, "qwen-custom")
        self.assertEqual(plan.settings.transcription_model, "custom-transcriber")
        self.assertEqual(plan.settings.local_whisper_prompt, "custom prompt")
        self.assertEqual(plan.settings.local_whisper_model, "models/custom.bin")
        self.assertEqual(plan.settings.local_whisper_language, "zh")
        self.assertEqual(settings.local_whisper_prompt, "default prompt")

    def test_openai_backend_loads_key_only_when_needed(self):
        with patch(
            "backend.services.processing_settings.load_openai_api_key",
            return_value="loaded-key",
        ) as load_key:
            plan = resolve_processing_plan(Settings(), transcription_backend="openai")

        self.assertEqual(plan.settings.openai_api_key, "loaded-key")
        self.assertEqual(plan.task_metadata(False)["transcription_model"], "gpt-4o-mini-transcribe")
        load_key.assert_called_once_with(required=True)

    def test_invalid_choices_fail_at_the_configuration_boundary(self):
        cases = (
            ({"notes_backend": "missing"}, "笔记引擎无效"),
            ({"note_style": "missing"}, "笔记风格无效"),
            ({"transcription_backend": "missing"}, "转录引擎无效"),
        )

        for overrides, message in cases:
            with self.subTest(overrides=overrides), self.assertRaisesRegex(RuntimeError, message):
                resolve_processing_plan(Settings(), **overrides)


if __name__ == "__main__":
    unittest.main()
