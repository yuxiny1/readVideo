import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.notes import (
    ArticleNote,
    ArticleSection,
    build_article_note_with_ollama,
    chunk_transcript,
    summarize_transcript,
    summarize_transcript_with_backend,
    summarize_transcript_with_ollama,
    write_markdown_note,
)


class NotesTest(unittest.TestCase):
    def test_chunk_transcript_groups_lines(self):
        chunks = chunk_transcript("第一行內容\n第二行內容\n第三行內容", max_chars=10)
        self.assertGreaterEqual(len(chunks), 2)

    def test_write_markdown_note_creates_summary_and_file(self):
        transcript = "\n".join(
            [
                "市場正在創新高但是宏觀情況仍然不確定",
                "美元石油體系正在受到去美元化的挑戰",
                "投資上可以保留現金並關注黃金和比特幣",
            ]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            result = write_markdown_note(
                transcript,
                "測試影片",
                "https://www.youtube.com/watch?v=test",
                tmpdir,
            )
            markdown = Path(result.markdown_path).read_text(encoding="utf-8")

        self.assertIn("# 測試影片", markdown)
        self.assertIn("## Summary", markdown)
        self.assertIn("## Segmented Notes", markdown)
        self.assertNotIn("## Full Transcript", markdown)
        self.assertNotIn("Transcript:", markdown)
        self.assertTrue(result.summary)

    def test_structured_note_uses_numbered_section_when_title_is_unclear(self):
        transcript = "\n".join(
            [
                "今天先讲第一个部分然后再讲第二个部分",
                "这里是一段普通转录内容没有明确主题标签",
                "后面继续补充一些背景和例子",
            ]
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            result = write_markdown_note(
                transcript,
                "普通影片",
                "https://www.youtube.com/watch?v=test",
                tmpdir,
            )
            markdown = Path(result.markdown_path).read_text(encoding="utf-8")

        self.assertIn("### Section 1", markdown)
        self.assertNotIn("Transcript Segment", markdown)

    def test_summarize_transcript_returns_limited_items(self):
        transcript = "\n".join(f"這是一段關於市場和美元體系的內容 {i}" for i in range(20))
        summary = summarize_transcript(transcript, max_items=3)
        self.assertLessEqual(len(summary), 3)

    def test_summarize_transcript_rejects_unknown_backend(self):
        with self.assertRaisesRegex(RuntimeError, "summary_backend"):
            summarize_transcript_with_backend("hello", backend="missing")

    def test_summarize_transcript_groups_contextual_topics(self):
        transcript = "\n".join(
            [
                "股市正在創新高",
                "但是背後的宏觀情況並不樂觀",
                "美元不再由黃金儲備支撐",
                "石油美元是全球金融秩序的核心系統",
                "去美元化讓各國開始降低美元儲備",
                "我會繼續持有充足的現金",
                "AI 的產業大概可以分為三層",
                "也記得一定要訂閱我的頻道",
            ]
        )
        summary = summarize_transcript(transcript)

        self.assertTrue(any(item.startswith("市場背景:") for item in summary))
        self.assertTrue(any(item.startswith("去美元化:") for item in summary))
        self.assertTrue(all("訂閱" not in item for item in summary))

    def test_summarize_transcript_handles_non_finance_topics(self):
        transcript = "\n".join(
            [
                "白领工作或者 knowledge worker 的核心价值在于认知中介",
                "很多人觉得工作没有意义是因为组织用 input 代理真正的 productivity",
                "AI 会让自动化变得更便宜也会改变生产力和生产关系",
                "个人应该把工作贴近可验收的结果并建立作品集",
            ]
        )
        summary = summarize_transcript(transcript)

        self.assertTrue(any(item.startswith("白领工作的本质:") for item in summary))
        self.assertTrue(any(item.startswith("个人应对:") for item in summary))

    def test_ollama_summary_summarizes_all_chunks_then_combines(self):
        transcript = "\n".join(
            [
                f"第一部分讲产品定位和用户问题 {index}"
                for index in range(10)
            ]
            + [
                f"第二部分讲执行步骤和后续行动 {index}"
                for index in range(10)
            ]
        )
        prompts = []

        def fake_request(prompt, model, url, timeout_seconds):
            prompts.append(prompt)
            if prompt.startswith("你是一个严谨"):
                return [f"片段要点: {len(prompts)}"]
            return ["全局总结: 覆盖产品定位、用户问题、执行步骤和后续行动"]

        with patch("backend.services.transcript_summarizer._request_ollama_summary", side_effect=fake_request):
            summary = summarize_transcript_with_ollama(transcript, chunk_chars=90)

        self.assertGreater(len(prompts), 2)
        self.assertIn("片段", prompts[0])
        self.assertIn("高质量中文总结", prompts[-1])
        self.assertEqual(summary, ["全局总结: 覆盖产品定位、用户问题、执行步骤和后续行动"])

    def test_ollama_article_note_builds_sections_from_full_chunks(self):
        transcript = "\n".join(
            [f"第一部分讲产品定位和用户问题 {index}" for index in range(10)]
            + [f"第二部分讲执行步骤和后续行动 {index}" for index in range(10)]
        )
        prompts = []

        def fake_request(prompt, model, url, timeout_seconds):
            prompts.append(prompt)
            if "中文长文编辑" in prompt:
                return "\n".join(
                    [
                        "## Summary",
                        "这节内容先从现代社会对计算技术的依赖讲起，再回到早期计算工具和机械计算的发展。",
                        "- 产品定位: 先定义用户问题，再说明产品要解决的核心场景。",
                        "- 执行路径: 后半段整理执行步骤和后续行动。",
                        "",
                        "## Sections",
                        "### 1. 产品定位",
                        "内容先解释用户问题，再把产品定位放在具体场景里。原文连续提到产品定位不是一句口号，而是要说明用户具体遇到什么阻碍、为什么现有方案不够用，以及这个产品准备如何降低使用门槛。",
                        "- 这一段还保留了用户问题 1、用户问题 2 和场景细节，而不是只写一个抽象结论。",
                        "",
                        "### 2. 执行路径",
                        "后半段说明执行步骤，并收束到下一步行动。",
                    ]
                )
            return "- 片段要点: 保留当前片段的关键事实\n- 章节主题: 产品定位"

        with patch("backend.services.transcript_summarizer._request_ollama_text", side_effect=fake_request):
            article = build_article_note_with_ollama(transcript, chunk_chars=90)

        self.assertGreater(len(prompts), 2)
        self.assertIn("片段 1/", prompts[0])
        self.assertIn("所有独立信息点", prompts[0])
        self.assertIn("完整性优先于简短", prompts[0])
        self.assertIn("文章式笔记", prompts[-1])
        self.assertIn("尽可能复原原文真正讲了什么", prompts[-1])
        self.assertIn("不能遗漏独立信息点", prompts[-1])
        self.assertEqual(article.summary_paragraphs[0], "这节内容先从现代社会对计算技术的依赖讲起，再回到早期计算工具和机械计算的发展。")
        self.assertEqual(article.summary_items[0], "产品定位: 先定义用户问题，再说明产品要解决的核心场景。")
        self.assertEqual([section.title for section in article.sections], ["产品定位", "执行路径"])
        self.assertIn("现有方案不够用", article.sections[0].body)
        self.assertIn("用户问题 2", article.sections[0].body)
        self.assertIn("下一步行动", article.sections[1].body)

    def test_write_markdown_note_uses_ollama_article_sections_without_full_transcript(self):
        article = ArticleNote(
            summary_items=["核心结论: 这节课把计算机科学入门拆成清晰路径。"],
            summary_paragraphs=["这节课把原始转录重新压缩成正文摘要，先交代课程目标，再说明学习路线。"],
            sections=[
                ArticleSection(
                    title="学习路线",
                    body="先建立课程地图，再理解每一讲之间的依赖关系。",
                )
            ],
        )
        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "backend.services.markdown_notes.build_article_note_with_ollama",
            return_value=article,
        ):
            result = write_markdown_note(
                "完整逐字稿第一行\n完整逐字稿第二行",
                "计算机科学入门",
                "https://www.bilibili.com/video/BV18s411A7Rj/",
                tmpdir,
                transcript_path="/tmp/transcript.txt",
                summary_backend="ollama",
            )
            markdown = Path(result.markdown_path).read_text(encoding="utf-8")

        self.assertIn("## Summary", markdown)
        self.assertIn("### Narrative Summary", markdown)
        self.assertIn("这节课把原始转录重新压缩成正文摘要", markdown)
        self.assertIn("## Segmented Notes", markdown)
        self.assertIn("### 1. 学习路线", markdown)
        self.assertIn("先建立课程地图", markdown)
        self.assertNotIn("## Full Transcript", markdown)
        self.assertNotIn("/tmp/transcript.txt", markdown)
        self.assertNotIn("完整逐字稿第二行", markdown)


if __name__ == "__main__":
    unittest.main()
