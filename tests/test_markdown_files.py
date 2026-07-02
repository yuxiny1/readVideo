import tempfile
import unittest
from pathlib import Path

from backend.services.markdown_files import list_markdown_files, read_markdown_file, resolve_markdown_file


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

            with self.assertRaisesRegex(ValueError, "只能下载 Markdown"):
                resolve_markdown_file(str(text_file))

    def test_list_markdown_files_rejects_missing_or_non_directory_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "note.md"
            file_path.write_text("# Note", encoding="utf-8")

            with self.assertRaises(FileNotFoundError):
                list_markdown_files(str(Path(tmpdir) / "missing"))
            with self.assertRaises(NotADirectoryError):
                list_markdown_files(str(file_path))

    def test_resolve_markdown_file_rejects_missing_markdown_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaises(FileNotFoundError):
                resolve_markdown_file(str(Path(tmpdir) / "missing.md"))

    def test_read_markdown_file_returns_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            note = Path(tmpdir) / "note.md"
            note.write_text("# Note\n\nBody", encoding="utf-8")

            document = read_markdown_file(str(note))

        self.assertEqual(document.name, "note.md")
        self.assertEqual(document.content, "# Note\n\nBody")

    def test_resolves_relative_notes_path_against_configured_container_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_dir = Path(tmpdir) / "mounted-notes"
            notes_dir.mkdir()
            note = notes_dir / "note.md"
            note.write_text("# Container note", encoding="utf-8")

            document = read_markdown_file("notes/note.md", str(notes_dir))

        self.assertEqual(document.path, str(note.resolve()))
        self.assertEqual(document.content, "# Container note")

    def test_resolves_legacy_absolute_notes_path_by_filename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_dir = Path(tmpdir) / "current-notes"
            notes_dir.mkdir()
            note = notes_dir / "legacy.md"
            note.write_text("# Legacy", encoding="utf-8")

            resolved = resolve_markdown_file(
                "/Users/example/readVideo/notes/legacy.md",
                str(notes_dir),
            )

        self.assertEqual(resolved, note.resolve())

    def test_maps_legacy_notes_directory_to_configured_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_dir = Path(tmpdir) / "mounted-notes"
            notes_dir.mkdir()

            resolved = list_markdown_files("notes", str(notes_dir))

        self.assertEqual(resolved, [])

    def test_maps_legacy_absolute_notes_directory_to_configured_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            notes_dir = Path(tmpdir) / "notes"
            notes_dir.mkdir()
            note = notes_dir / "legacy.md"
            note.write_text("# Legacy", encoding="utf-8")

            files = list_markdown_files("/Users/example/readVideo/notes", str(notes_dir))

        self.assertEqual([item.name for item in files], ["legacy.md"])


if __name__ == "__main__":
    unittest.main()
