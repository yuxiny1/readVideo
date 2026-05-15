import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from backend.services.transcript_summarizer import section_title, summarize_transcript_with_backend


@dataclass(frozen=True)
class NoteResult:
    markdown_path: str
    summary: str
    section_count: int
    summary_backend: str = "extractive"


def write_markdown_note(
    transcript_text: str,
    video_title: str,
    source_url: str,
    output_dir: str,
    transcript_path: Optional[str] = None,
    summary_backend: str = "extractive",
    ollama_model: str = "qwen2.5:3b",
    ollama_url: str = "http://127.0.0.1:11434/api/generate",
) -> NoteResult:
    sections = chunk_transcript(transcript_text)
    summary_items = summarize_transcript_with_backend(
        transcript_text,
        backend=summary_backend,
        ollama_model=ollama_model,
        ollama_url=ollama_url,
    )
    markdown = render_markdown_note(
        video_title=video_title,
        source_url=source_url,
        transcript_text=transcript_text,
        sections=sections,
        summary_items=summary_items,
        transcript_path=transcript_path,
    )

    notes_dir = Path(output_dir).expanduser()
    notes_dir.mkdir(parents=True, exist_ok=True)
    note_path = notes_dir / f"{safe_filename(video_title)}.md"
    note_path.write_text(markdown, encoding="utf-8")

    return NoteResult(
        markdown_path=str(note_path),
        summary="\n".join(f"- {item}" for item in summary_items),
        section_count=len(sections),
        summary_backend=summary_backend,
    )


def chunk_transcript(transcript_text: str, max_chars: int = 900) -> list[str]:
    lines = [line.strip() for line in transcript_text.splitlines() if line.strip()]
    chunks = []
    current = []
    current_len = 0

    for line in lines:
        if current and current_len + len(line) > max_chars:
            chunks.append(" ".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += len(line)

    if current:
        chunks.append(" ".join(current))

    return chunks


def render_markdown_note(
    video_title: str,
    source_url: str,
    transcript_text: str,
    sections: Iterable[str],
    summary_items: Iterable[str],
    transcript_path: Optional[str] = None,
) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# {video_title}",
        "",
        f"- Source: {source_url}",
        f"- Generated: {generated_at}",
    ]
    if transcript_path:
        lines.append(f"- Transcript: `{transcript_path}`")

    lines.extend(["", "## Summary", ""])
    summary_items = list(summary_items)
    if summary_items:
        lines.extend(f"- {item}" for item in summary_items)
    else:
        lines.append("- No summary could be generated.")

    lines.extend(["", "## Structured Notes", ""])
    for index, section in enumerate(sections, start=1):
        title = section_title(section, index=index)
        heading = title if title.startswith("Section ") else f"{index}. {title}"
        lines.extend([f"### {heading}", "", section, ""])

    lines.extend(["## Full Transcript", "", transcript_text.strip(), ""])
    return "\n".join(lines)


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]+", "-", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:180] or "readvideo-note"
