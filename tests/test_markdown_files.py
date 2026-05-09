import tempfile
import unittest
from pathlib import Path

from backend.services.markdown_files import list_markdown_files, resolve_markdown_file


class MarkdownFilesTest(unittest.TestCase):
    def test_list_markdown_files_returns_only_markdown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            note = folder / "note.md"
            note.write_text("# Note", encoding="utf-8")
            (folder / "ignore.txt").write_text("nope", encoding="utf-8")

            files = list_markdown_files(str(folder))

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].name, "note.md")
        self.assertEqual(files[0].size_bytes, 6)

    def test_resolve_markdown_file_rejects_non_markdown(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            text_file = Path(tmpdir) / "note.txt"
            text_file.write_text("No", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Only Markdown"):
                resolve_markdown_file(str(text_file))


if __name__ == "__main__":
    unittest.main()
