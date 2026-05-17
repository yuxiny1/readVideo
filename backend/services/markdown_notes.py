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
    ollama_model: str = "qwen2.5:32b",
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
    ollama_model: str = "qwen2.5:32b",
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
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += len(line)

    if current:
        chunks.append("\n".join(current))

    return chunks


def original_transcript_segments(transcript_text: str, section_count: int) -> list[str]:
    lines = [line.strip() for line in transcript_text.splitlines() if line.strip()]
    if not lines or section_count <= 0:
        return []
    if section_count == 1:
        return ["\n".join(lines)]

    target_chars = max(1, sum(len(line) for line in lines) // section_count)
    segments: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in lines:
        if current and len(segments) < section_count - 1 and current_len + len(line) > target_chars:
            segments.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += len(line)

    if current:
        segments.append("\n".join(current))

    while len(segments) < section_count:
        segments.append("")

    if len(segments) > section_count:
        merged_tail = "\n".join(segment for segment in segments[section_count - 1 :] if segment)
        segments = segments[: section_count - 1] + [merged_tail]

    return segments


def original_transcript_segments_for_sections(
    transcript_text: str,
    sections: Iterable[ArticleSection],
) -> list[str]:
    article_sections = list(sections)
    if not article_sections:
        return []

    transcript_chunks = chunk_transcript(transcript_text, max_chars=900)
    if not transcript_chunks:
        return []

    candidates = _original_transcript_candidates(transcript_chunks)
    if not candidates:
        return original_transcript_segments(transcript_text, len(article_sections))

    matched_segments = []
    for section in article_sections:
        matched_segments.append(_best_original_segment(section, candidates))
    return matched_segments


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
    article_sections = [_coerce_section(section, index) for index, section in enumerate(sections, start=1)]
    raw_segments = original_transcript_segments_for_sections(transcript_text, article_sections)
    for index, article_section in enumerate(article_sections, start=1):
        title = article_section.title
        heading = title if title.startswith("Section ") else f"{index}. {title}"
        lines.extend([f"### {heading}", "", article_section.body, ""])
        original_segment = raw_segments[index - 1] if index - 1 < len(raw_segments) else ""
        if original_segment:
            lines.extend(["#### Original Transcript", "", "```text", original_segment.strip(), "```", ""])

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


def _original_transcript_candidates(transcript_chunks: list[str]) -> list[str]:
    return transcript_chunks


def _best_original_segment(section: ArticleSection, candidates: list[str]) -> str:
    query_text = _expand_original_transcript_query(f"{section.title}\n{section.body}")
    query_tokens = _matching_tokens(query_text)
    if not query_tokens:
        return candidates[0]

    best_score = -1
    best_candidate = candidates[0]
    for candidate in candidates:
        candidate_tokens = _matching_tokens(candidate)
        overlap = query_tokens & candidate_tokens
        score = len(overlap) * 10
        score += _phrase_score(query_text, candidate)
        score += min(len(candidate), 1600) / 1000
        if score > best_score:
            best_score = score
            best_candidate = candidate
    return best_candidate


def _expand_original_transcript_query(text: str) -> str:
    aliases = {
        "美伊": "iran war trump",
        "伊朗": "iran",
        "战争": "war pearl harbor winners losers neutral countries",
        "金融市场": "markets debt equity cash flow earnings",
        "市场": "markets cash flow earnings",
        "长期投资": "long-term investments geopolitics bridgewater",
        "地缘政治": "geopolitics great economic powers",
        "赢家": "winners losers neutral countries",
        "输家": "winners losers neutral countries",
        "中立": "neutral countries",
        "中国": "china chinese",
        "崛起": "rise relative power",
        "朝贡": "tribute system",
        "体系": "system",
        "军事基地": "bases 750 80 countries defend",
        "基地": "bases 750 80 countries defend",
        "制衡": "countervailing force",
        "人民币": "rmb world currency",
        "投资者": "investors diversification liquidity gold",
    }
    expanded = [text]
    for keyword, alias in aliases.items():
        if keyword.lower() in text.lower():
            expanded.append(alias)
    return " ".join(expanded)


def _matching_tokens(text: str) -> set[str]:
    stopwords = {
        "the",
        "and",
        "that",
        "this",
        "with",
        "have",
        "will",
        "they",
        "there",
        "from",
        "into",
        "about",
        "because",
        "their",
    }
    ascii_words = {
        word
        for word in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", text.lower())
        if word not in stopwords
    }
    chinese_words = set(re.findall(r"[\u4e00-\u9fff]{2,4}", text))
    numbers = set(re.findall(r"\b\d+\b", text))
    return ascii_words | chinese_words | numbers


def _phrase_score(query_text: str, candidate: str) -> int:
    score = 0
    candidate_lower = candidate.lower()
    for phrase in (
        "ray dalio",
        "bridgewater",
        "cash flow",
        "pearl harbor",
        "neutral countries",
        "tribute system",
        "750 bases",
        "world currency",
    ):
        if phrase in query_text.lower() and phrase in candidate_lower:
            score += 30
    return score


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]+", "-", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:180] or "readvideo-note"
