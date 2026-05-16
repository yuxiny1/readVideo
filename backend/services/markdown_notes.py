import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from backend.services.transcript_summarizer import (
    ArticleNote,
    ArticleSection,
    build_article_note_with_ollama,
    section_title,
    summarize_transcript,
    summarize_transcript_with_backend,
)


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
    article_note = build_article_note(
        transcript_text,
        summary_backend=summary_backend,
        ollama_model=ollama_model,
        ollama_url=ollama_url,
    )
    markdown = render_markdown_note(
        video_title=video_title,
        source_url=source_url,
        transcript_text=transcript_text,
        sections=article_note.sections,
        summary_items=article_note.summary_items,
        transcript_path=transcript_path,
        summary_paragraphs=article_note.summary_paragraphs,
    )

    notes_dir = Path(output_dir).expanduser()
    notes_dir.mkdir(parents=True, exist_ok=True)
    note_path = notes_dir / f"{safe_filename(video_title)}.md"
    note_path.write_text(markdown, encoding="utf-8")

    return NoteResult(
        markdown_path=str(note_path),
        summary=render_summary_text(article_note),
        section_count=len(article_note.sections),
        summary_backend=summary_backend,
    )


def build_article_note(
    transcript_text: str,
    summary_backend: str = "extractive",
    ollama_model: str = "qwen2.5:3b",
    ollama_url: str = "http://127.0.0.1:11434/api/generate",
) -> ArticleNote:
    if summary_backend == "ollama":
        article_note = build_article_note_with_ollama(
            transcript_text,
            model=ollama_model,
            url=ollama_url,
        )
        return ArticleNote(
            summary_items=article_note.summary_items or summarize_transcript(transcript_text),
            sections=article_note.sections or _extractive_sections(transcript_text),
            summary_paragraphs=article_note.summary_paragraphs,
        )

    summary_items = summarize_transcript_with_backend(
        transcript_text,
        backend=summary_backend,
        ollama_model=ollama_model,
        ollama_url=ollama_url,
    )
    return ArticleNote(
        summary_items=summary_items,
        sections=_extractive_sections(transcript_text),
        summary_paragraphs=_paragraphs_from_summary_items(summary_items),
    )


def _extractive_sections(transcript_text: str) -> list[ArticleSection]:
    return [
        ArticleSection(title=section_title(section, index=index), body=section)
        for index, section in enumerate(chunk_transcript(transcript_text), start=1)
    ]


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
    sections: Iterable[ArticleSection | str],
    summary_items: Iterable[str],
    transcript_path: Optional[str] = None,
    summary_paragraphs: Optional[Iterable[str]] = None,
) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# {video_title}",
        "",
        f"- Source: {source_url}",
        f"- Generated: {generated_at}",
    ]

    lines.extend(["", "## Summary", ""])
    summary_items = list(summary_items)
    summary_paragraphs = list(summary_paragraphs or [])
    if summary_items:
        lines.extend(f"- {item}" for item in summary_items)
    else:
        lines.append("- No summary could be generated.")
    if summary_paragraphs:
        lines.extend(["", "### Narrative Summary", ""])
        for paragraph in summary_paragraphs:
            lines.extend([paragraph, ""])

    lines.extend(["", "## Segmented Notes", ""])
    for index, section in enumerate(sections, start=1):
        article_section = _coerce_section(section, index)
        title = article_section.title
        heading = title if title.startswith("Section ") else f"{index}. {title}"
        lines.extend([f"### {heading}", "", article_section.body, ""])

    return "\n".join(lines)


def render_summary_text(article_note: ArticleNote) -> str:
    parts: list[str] = []
    if article_note.summary_paragraphs:
        parts.extend(article_note.summary_paragraphs)
    if article_note.summary_items:
        if parts:
            parts.append("")
        parts.extend(f"- {item}" for item in article_note.summary_items)
    return "\n".join(parts)


def _paragraphs_from_summary_items(summary_items: list[str], max_items: int = 5) -> list[str]:
    if not summary_items:
        return []
    fragments = [re.sub(r"^[^:：]{2,18}[:：]\s*", "", item).strip() for item in summary_items[:max_items]]
    fragments = [fragment for fragment in fragments if fragment]
    if not fragments:
        return []
    return ["；".join(fragments).rstrip("；。") + "。"]


def _coerce_section(section: ArticleSection | str, index: int) -> ArticleSection:
    if isinstance(section, ArticleSection):
        return section
    return ArticleSection(title=section_title(section, index=index), body=section)


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]+", "-", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:180] or "readvideo-note"
