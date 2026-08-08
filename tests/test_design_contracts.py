import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DesignContractTest(unittest.TestCase):
    def test_controllers_do_not_bypass_cqrs_handlers(self):
        controller_root = PROJECT_ROOT / "backend" / "api" / "controllers"
        forbidden_prefixes = ("backend.services", "backend.storage")
        violations = []
        for path in controller_root.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                module = node.module if isinstance(node, ast.ImportFrom) else ""
                names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else []
                imported = [module, *names]
                if any(name.startswith(forbidden_prefixes) for name in imported):
                    violations.append(path.relative_to(PROJECT_ROOT).as_posix())
        self.assertEqual(violations, [], f"Controllers bypassed CQRS boundaries: {violations}")

    def test_coordination_modules_remain_small(self):
        modules = [
            "backend/application/handlers/tasks.py",
            "backend/services/markdown_notes.py",
            "backend/services/transcript_summarizer.py",
            "backend/services/video_processor.py",
        ]
        oversized = {}
        for relative_path in modules:
            line_count = len((PROJECT_ROOT / relative_path).read_text(encoding="utf-8").splitlines())
            if line_count > 300:
                oversized[relative_path] = line_count
        self.assertEqual(oversized, {}, f"Coordination modules expose too much complexity: {oversized}")

    def test_video_processor_delegates_specialized_knowledge(self):
        source = (PROJECT_ROOT / "backend/services/video_processor.py").read_text(encoding="utf-8")
        for module in ["download_progress", "processing_settings", "transcription_gateway"]:
            self.assertIn(f"backend.services.{module}", source)
        self.assertNotIn("LocalWhisperTranscription", source)
        self.assertNotIn("AudioTranscription", source)
        self.assertNotIn("load_openai_api_key", source)

    def test_transcript_summary_facade_hides_transport_and_parsing(self):
        source = (PROJECT_ROOT / "backend/services/transcript_summarizer.py").read_text(encoding="utf-8")
        self.assertIn("__all__", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("json", source)
        self.assertNotIn("re.", source)

    def test_repository_documents_design_ownership(self):
        source = (PROJECT_ROOT / "docs/software-design-principles.md").read_text(encoding="utf-8")
        for principle in ["模块要深", "隐藏知识", "把复杂度向下拉", "定义掉可以避免的错误", "先比较两个设计"]:
            self.assertIn(principle, source)


if __name__ == "__main__":
    unittest.main()
