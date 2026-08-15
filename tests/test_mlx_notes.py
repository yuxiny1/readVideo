import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from backend.services.markdown_notes import write_markdown_note
from backend.services.note_models import ArticleNote, ArticleSection
from backend.services.mlx_notes import build_article_note_with_mlx, summarize_transcript_with_mlx


class MlxNotesTest(unittest.TestCase):
    @patch("backend.services.mlx_notes.MlxClient.generate", autospec=True)
    def test_mlx_uses_the_shared_detailed_note_workflow(self, generate):
        generate.return_value = "\n".join(
            [
                "## 总结",
                "这段内容解释本地模型如何生成结构化笔记。",
                "- 核心流程: 先转录，再整理文章式笔记。",
                "",
                "## 分段笔记",
                "### 1. 本地处理流程",
                "视频先完成转录，然后由本地模型整理成结构化文章。",
            ]
        )

        article = build_article_note_with_mlx("视频先转录，再由本地模型生成结构化笔记。")

        self.assertEqual(article.summary_items, ["核心流程: 先转录，再整理文章式笔记。"])
        self.assertEqual(article.sections[0].title, "本地处理流程")
        prompt = generate.call_args.args[1]
        self.assertIn("中文长文编辑", prompt)
        self.assertIn("不能遗漏独立信息点", prompt)

    @patch("backend.services.mlx_notes.MlxClient.generate", autospec=True)
    def test_mlx_summary_uses_markdown_bullets(self, generate):
        generate.return_value = "- 模型用途: 在本机整理视频笔记。"

        summary = summarize_transcript_with_mlx("在本机使用模型整理视频笔记。")

        self.assertEqual(summary, ["模型用途: 在本机整理视频笔记。"])

    @patch("backend.services.markdown_notes.build_article_note_with_mlx")
    def test_markdown_writer_dispatches_mlx_without_changing_the_note_format(self, build_note):
        build_note.return_value = ArticleNote(
            summary_items=["本地模型: 使用 MLX 整理笔记。"],
            sections=[ArticleSection(title="处理过程", body="视频先完成转录，再生成笔记。")],
            summary_paragraphs=["这段内容解释 MLX 本地笔记流程。"],
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            result = write_markdown_note(
                "视频先完成转录，再生成笔记。",
                "MLX 测试",
                "https://example.com/video",
                tmpdir,
                summary_backend="mlx",
                mlx_model="mlx/model",
                mlx_url="http://mlx/v1/chat/completions",
            )
            markdown = Path(result.markdown_path).read_text(encoding="utf-8")

        build_note.assert_called_once_with(
            "视频先完成转录，再生成笔记。",
            model="mlx/model",
            url="http://mlx/v1/chat/completions",
            note_style="detailed",
        )
        self.assertEqual(result.summary_backend, "mlx")
        self.assertIn("## 分段笔记", markdown)


if __name__ == "__main__":
    unittest.main()
