from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class MarkdownFile:
    name: str
    path: str
    directory: str
    size_bytes: int
    modified_at: str


@dataclass(frozen=True)
class MarkdownDocument:
    name: str
    path: str
    directory: str
    content: str
    modified_at: str


def list_markdown_files(directory: str, notes_dir: str | None = None) -> list[MarkdownFile]:
    folder = resolve_markdown_directory(directory, notes_dir)
    if not folder.exists():
        raise FileNotFoundError(f"Markdown 文件夹不存在：{directory}")
    if not folder.is_dir():
        raise NotADirectoryError(f"Markdown 路径不是文件夹：{directory}")

    files = sorted(folder.glob("*.md"), key=lambda path: path.stat().st_mtime, reverse=True)
    return [_file_to_record(path) for path in files if path.is_file()]


def resolve_markdown_directory(directory: str, notes_dir: str | None = None) -> Path:
    requested = Path(directory).expanduser()
    candidates = [requested]
    if not requested.is_absolute():
        candidates.append(PROJECT_ROOT / requested)
    if notes_dir:
        notes_root = Path(notes_dir).expanduser()
        if not notes_root.is_absolute():
            notes_root = PROJECT_ROOT / notes_root
        if directory in {"", ".", "notes", notes_root.name} or requested.name in {"notes", notes_root.name}:
            candidates.insert(0, notes_root)
    for candidate in candidates:
        if candidate.is_dir():
            return candidate.resolve()
    return candidates[0]


def resolve_markdown_file(path: str, notes_dir: str | None = None) -> Path:
    requested = Path(path).expanduser()
    markdown_path = requested
    if markdown_path.suffix.lower() != ".md":
        raise ValueError("只能下载 Markdown 文件。")

    candidates = [requested]
    if not requested.is_absolute():
        candidates.append(PROJECT_ROOT / requested)
    if notes_dir:
        notes_root = Path(notes_dir).expanduser()
        if not notes_root.is_absolute():
            notes_root = PROJECT_ROOT / notes_root
        candidates.append(notes_root / _notes_relative_path(requested, notes_root.name))

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(f"Markdown 文件不存在：{path}")


def read_markdown_file(path: str, notes_dir: str | None = None) -> MarkdownDocument:
    markdown_path = resolve_markdown_file(path, notes_dir)
    stats = markdown_path.stat()
    return MarkdownDocument(
        name=markdown_path.name,
        path=str(markdown_path),
        directory=str(markdown_path.parent),
        content=markdown_path.read_text(encoding="utf-8"),
        modified_at=datetime.fromtimestamp(stats.st_mtime).isoformat(timespec="seconds"),
    )


def _file_to_record(path: Path) -> MarkdownFile:
    stats = path.stat()
    return MarkdownFile(
        name=path.name,
        path=str(path),
        directory=str(path.parent),
        size_bytes=stats.st_size,
        modified_at=datetime.fromtimestamp(stats.st_mtime).isoformat(timespec="seconds"),
    )


def _notes_relative_path(path: Path, notes_root_name: str) -> Path:
    parts = list(path.parts)
    marker_indexes = [index for index, part in enumerate(parts) if part in {"notes", notes_root_name}]
    relative_parts = parts[marker_indexes[-1] + 1:] if marker_indexes else [path.name]
    safe_parts = [part for part in relative_parts if part not in {"", ".", "..", path.anchor}]
    return Path(*safe_parts) if safe_parts else Path(path.name)
