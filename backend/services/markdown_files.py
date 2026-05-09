from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class MarkdownFile:
    name: str
    path: str
    directory: str
    size_bytes: int
    modified_at: str


def list_markdown_files(directory: str) -> list[MarkdownFile]:
    folder = Path(directory).expanduser()
    if not folder.exists():
        raise FileNotFoundError(f"Markdown folder does not exist: {directory}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Markdown path is not a folder: {directory}")

    files = sorted(folder.glob("*.md"), key=lambda path: path.stat().st_mtime, reverse=True)
    return [_file_to_record(path) for path in files if path.is_file()]


def resolve_markdown_file(path: str) -> Path:
    markdown_path = Path(path).expanduser()
    if markdown_path.suffix.lower() != ".md":
        raise ValueError("Only Markdown files can be downloaded.")
    if not markdown_path.exists() or not markdown_path.is_file():
        raise FileNotFoundError(f"Markdown file does not exist: {path}")
    return markdown_path


def _file_to_record(path: Path) -> MarkdownFile:
    stats = path.stat()
    return MarkdownFile(
        name=path.name,
        path=str(path),
        directory=str(path.parent),
        size_bytes=stats.st_size,
        modified_at=datetime.fromtimestamp(stats.st_mtime).isoformat(timespec="seconds"),
    )
