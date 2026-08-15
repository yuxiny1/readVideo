import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from backend.services.commercial_note_fallback import (
    fallback_business_lens,
    fallback_editorial_paragraphs,
)
from backend.services.transcript_summarizer import (
    ArticleNote,
    ArticleSection,
    build_article_note_with_ollama,
    build_article_note_with_mlx,
    section_title,
    summarize_transcript,
    summarize_transcript_with_backend,
)
from backend.services.transcript_segments import (
    chunk_transcript,
    original_transcript_segments,
    original_transcript_segments_for_sections,
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
    ollama_model: str = "qwen3.6:35b",
    ollama_url: str = "http://127.0.0.1:11434/api/generate",
    note_style: str = "detailed",
    mlx_model: str = "mlx-community/Qwen2.5-72B-Instruct-3bit",
    mlx_url: str = "http://127.0.0.1:8080/v1/chat/completions",
) -> NoteResult:
    article_note = build_article_note(
        transcript_text,
        summary_backend=summary_backend,
        ollama_model=ollama_model,
        ollama_url=ollama_url,
        mlx_model=mlx_model,
        mlx_url=mlx_url,
        note_style=note_style,
    )
    markdown = render_markdown_note(
        video_title=video_title,
        source_url=source_url,
        transcript_text=transcript_text,
        sections=article_note.sections,
        summary_items=article_note.summary_items,
        transcript_path=transcript_path,
        summary_paragraphs=article_note.summary_paragraphs,
        business_items=article_note.business_items,
        editorial_paragraphs=article_note.editorial_paragraphs,
        note_style=note_style,
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
    ollama_model: str = "qwen3.6:35b",
    ollama_url: str = "http://127.0.0.1:11434/api/generate",
    note_style: str = "detailed",
    mlx_model: str = "mlx-community/Qwen2.5-72B-Instruct-3bit",
    mlx_url: str = "http://127.0.0.1:8080/v1/chat/completions",
) -> ArticleNote:
    if summary_backend == "ollama":
        article_note = build_article_note_with_ollama(
            transcript_text,
            model=ollama_model,
            url=ollama_url,
            note_style=note_style,
        )
        return ArticleNote(
            summary_items=article_note.summary_items or summarize_transcript(transcript_text),
            sections=article_note.sections or _extractive_sections(transcript_text),
            summary_paragraphs=article_note.summary_paragraphs,
            business_items=article_note.business_items,
            editorial_paragraphs=article_note.editorial_paragraphs,
        )

    if summary_backend == "mlx":
        article_note = build_article_note_with_mlx(
            transcript_text,
            model=mlx_model,
            url=mlx_url,
            note_style=note_style,
        )
        return ArticleNote(
            summary_items=article_note.summary_items or summarize_transcript(transcript_text),
            sections=article_note.sections or _extractive_sections(transcript_text),
            summary_paragraphs=article_note.summary_paragraphs,
            business_items=article_note.business_items,
            editorial_paragraphs=article_note.editorial_paragraphs,
        )

    summary_items = summarize_transcript_with_backend(
        transcript_text,
        backend=summary_backend,
        ollama_model=ollama_model,
        ollama_url=ollama_url,
        mlx_model=mlx_model,
        mlx_url=mlx_url,
    )
    return ArticleNote(
        summary_items=summary_items,
        sections=_extractive_sections(transcript_text),
        summary_paragraphs=_paragraphs_from_summary_items(summary_items),
        business_items=[],
        editorial_paragraphs=[],
    )


def _extractive_sections(transcript_text: str) -> list[ArticleSection]:
    return [
        ArticleSection(title=section_title(section, index=index), body=section)
        for index, section in enumerate(chunk_transcript(transcript_text), start=1)
    ]


def render_markdown_note(
    video_title: str,
    source_url: str,
    transcript_text: str,
    sections: Iterable[ArticleSection | str],
    summary_items: Iterable[str],
    transcript_path: Optional[str] = None,
    summary_paragraphs: Optional[Iterable[str]] = None,
    business_items: Optional[Iterable[str]] = None,
    editorial_paragraphs: Optional[Iterable[str]] = None,
    note_style: str = "detailed",
) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# {video_title}",
        "",
        f"- 来源：{source_url}",
        f"- 生成时间：{generated_at}",
    ]
    if transcript_path:
        lines.append(f"- 转录文件：`{transcript_path}`")

    lines.extend(["", "## 总结", ""])
    summary_items = list(summary_items)
    summary_paragraphs = list(summary_paragraphs or [])
    article_sections = [_coerce_section(section, index) for index, section in enumerate(sections, start=1)]
    if summary_items:
        lines.extend(f"- {item}" for item in summary_items)
    else:
        lines.append("- 无法生成总结。")
    if summary_paragraphs:
        lines.extend(["", "### 内容概览", ""])
        for paragraph in summary_paragraphs:
            lines.extend([paragraph, ""])

    business_items = list(business_items or [])
    editorial_paragraphs = list(editorial_paragraphs or [])
    if note_style == "commercial":
        business_items = business_items or fallback_business_lens(
            video_title,
            summary_items,
            summary_paragraphs,
            article_sections,
        )
        if business_items:
            lines.extend(["", "## 商业视角", ""])
            lines.extend(f"- {item}" for item in business_items[:8])
            lines.append("")

        editorial_paragraphs = editorial_paragraphs or fallback_editorial_paragraphs(
            video_title,
            summary_items,
            summary_paragraphs,
            article_sections,
        )
        if editorial_paragraphs:
            lines.extend(["", "## 商业分析", ""])
            for paragraph in editorial_paragraphs:
                lines.extend([paragraph, ""])

    lines.extend(["", "## 分段笔记", ""])
    raw_segments = original_transcript_segments_for_sections(transcript_text, article_sections)
    for index, article_section in enumerate(article_sections, start=1):
        title = article_section.title
        heading = title if re.match(r"^第\s*\d+\s*节$", title) else f"{index}. {title}"
        lines.extend([f"### {heading}", "", article_section.body, ""])
        original_segment = raw_segments[index - 1] if index - 1 < len(raw_segments) else ""
        if original_segment:
            lines.extend(["#### 原文片段", "", "```text", original_segment.strip(), "```", ""])

    return "\n".join(lines)


def render_summary_text(article_note: ArticleNote) -> str:
    parts: list[str] = []
    if article_note.summary_paragraphs:
        parts.extend(article_note.summary_paragraphs)
    if article_note.business_items:
        if parts:
            parts.append("")
        parts.extend(f"- {item}" for item in article_note.business_items[:5])
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
    return cleaned[:180] or "readvideo-笔记"
