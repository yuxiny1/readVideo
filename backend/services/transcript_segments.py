import re
from typing import Iterable

from backend.services.note_models import ArticleSection


def chunk_transcript(transcript_text: str, max_chars: int = 900) -> list[str]:
    lines = [line.strip() for line in transcript_text.splitlines() if line.strip()]
    chunks: list[str] = []
    current: list[str] = []
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
        merged_tail = "\n".join(segment for segment in segments[section_count - 1:] if segment)
        segments = segments[:section_count - 1] + [merged_tail]
    return segments


def original_transcript_segments_for_sections(
    transcript_text: str,
    sections: Iterable[ArticleSection],
) -> list[str]:
    article_sections = list(sections)
    if not article_sections:
        return []
    candidates = chunk_transcript(transcript_text, max_chars=900)
    if not candidates:
        return []
    return [_best_original_segment(section, candidates) for section in article_sections]


def _best_original_segment(section: ArticleSection, candidates: list[str]) -> str:
    query_text = _expand_query(f"{section.title}\n{section.body}")
    query_tokens = _matching_tokens(query_text)
    if not query_tokens:
        return candidates[0]

    def score(candidate: str) -> float:
        overlap = query_tokens & _matching_tokens(candidate)
        return (
            len(overlap) * 10
            + _phrase_score(query_text, candidate)
            + min(len(candidate), 1600) / 1000
        )

    return max(candidates, key=score)


def _expand_query(text: str) -> str:
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
        "the", "and", "that", "this", "with", "have", "will", "they", "there", "from",
        "into", "about", "because", "their",
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
    query_lower = query_text.lower()
    candidate_lower = candidate.lower()
    phrases = (
        "ray dalio", "bridgewater", "cash flow", "pearl harbor", "neutral countries",
        "tribute system", "750 bases", "world currency",
    )
    return sum(30 for phrase in phrases if phrase in query_lower and phrase in candidate_lower)
