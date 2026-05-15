import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services.notes import (
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
        self.assertIn("## Structured Notes", markdown)
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


if __name__ == "__main__":
    unittest.main()
