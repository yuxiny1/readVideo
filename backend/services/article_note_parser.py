import re

from backend.services.note_models import ArticleNote, ArticleSection
from backend.services.transcript_text import (
    dedupe_items,
    dedupe_paragraphs,
    is_promotional,
    paragraphs_from_summary_items,
    trim_sentence,
)


def parse_article_note(text: str, max_summary_items: int = 7, max_sections: int = 8) -> ArticleNote:
    summary_items: list[str] = []
    summary_paragraphs: list[str] = []
    summary_paragraph_lines: list[str] = []
    business_items: list[str] = []
    editorial_paragraphs: list[str] = []
    editorial_lines: list[str] = []
    sections: list[ArticleSection] = []
    mode = ""
    current_title = ""
    current_body: list[str] = []

    def flush_section():
        nonlocal current_title, current_body
        body = _clean_section_body("\n".join(current_body))
        title = _clean_section_title(current_title, len(sections) + 1)
        if body:
            sections.append(ArticleSection(title=title, body=body))
        current_title = ""
        current_body = []

    def flush_summary_paragraph():
        nonlocal summary_paragraph_lines
        paragraph = _clean_summary_paragraph(" ".join(summary_paragraph_lines))
        if paragraph:
            summary_paragraphs.append(paragraph)
        summary_paragraph_lines = []

    def flush_editorial_paragraph():
        nonlocal editorial_lines
        paragraph = _clean_editorial_paragraph(" ".join(editorial_lines))
        if paragraph:
            editorial_paragraphs.append(paragraph)
        editorial_lines = []

    for raw_line in text.splitlines():
        stripped = raw_line.rstrip().strip()
        if not stripped:
            if mode == "summary":
                flush_summary_paragraph()
                continue
            if mode == "editorial":
                flush_editorial_paragraph()
                continue
            if current_body:
                current_body.append("")
            continue

        heading_match = re.match(r"^(#{1,4})\s+(.+?)\s*$", stripped)
        if heading_match:
            heading_text = heading_match.group(2).strip()
            heading_lower = heading_text.lower()
            if any(word in heading_lower for word in ("summary", "摘要", "总结", "總結", "要点", "要點")):
                flush_summary_paragraph()
                flush_editorial_paragraph()
                flush_section()
                mode = "summary"
                continue
            if any(word in heading_lower for word in (
                "business lens", "business takeaways", "business brief", "商业视角", "商業視角",
                "商业判断", "商業判斷", "商业要点", "商業要點",
            )):
                flush_summary_paragraph()
                flush_editorial_paragraph()
                flush_section()
                mode = "business"
                continue
            if any(word in heading_lower for word in (
                "editorial", "commercial article", "商业文章", "商業文章", "商业新闻", "商業新聞",
                "商业分析", "商業分析",
            )):
                flush_summary_paragraph()
                flush_editorial_paragraph()
                flush_section()
                mode = "editorial"
                continue
            if mode == "summary" and any(word in heading_lower for word in ("key points", "要点", "要點", "重点", "重點")):
                flush_summary_paragraph()
                continue
            if mode == "editorial" and _is_editorial_label(heading_text):
                flush_editorial_paragraph()
                continue
            if mode == "business" and heading_match.group(1) in {"###", "####"}:
                continue
            if any(word in heading_lower for word in (
                "section", "sections", "章节", "章節", "分段", "正文", "笔记", "筆記",
            )) and heading_match.group(1) in {"#", "##"}:
                flush_summary_paragraph()
                flush_editorial_paragraph()
                flush_section()
                mode = "sections"
                continue
            if mode == "sections" or heading_match.group(1) in {"###", "####"}:
                flush_summary_paragraph()
                flush_editorial_paragraph()
                flush_section()
                mode = "sections"
                current_title = heading_text
                continue

        if mode == "summary":
            item = _parse_summary_line(stripped)
            if item:
                flush_summary_paragraph()
                summary_items.append(item)
            elif not _is_summary_label(stripped):
                summary_paragraph_lines.append(stripped)
            continue
        if mode == "business":
            item = _parse_business_line(stripped)
            if item:
                business_items.append(item)
            continue
        if mode == "editorial":
            if not _is_editorial_label(stripped):
                editorial_lines.append(stripped)
            continue
        if mode == "sections":
            current_body.append(stripped)
            continue

        item = _parse_summary_line(stripped)
        if item and len(summary_items) < max_summary_items:
            summary_items.append(item)

    flush_summary_paragraph()
    flush_editorial_paragraph()
    flush_section()
    if not sections:
        sections = _parse_numbered_sections(text, max_sections)

    summary_items = dedupe_items(summary_items)[:max_summary_items]
    summary_paragraphs = dedupe_paragraphs(summary_paragraphs) or paragraphs_from_summary_items(summary_items)
    return ArticleNote(
        summary_items=summary_items,
        sections=sections[:max_sections],
        summary_paragraphs=summary_paragraphs[:2],
        business_items=dedupe_items(business_items)[:8],
        editorial_paragraphs=dedupe_paragraphs(editorial_paragraphs)[:8],
    )


def _parse_summary_line(line: str) -> str:
    has_marker = re.match(r"^\s*(?:[-*]|\d+[.)])\s+", line)
    item = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip().strip("-* ")
    if not item or is_promotional(item):
        return ""
    if not has_marker and ":" not in item and "：" not in item:
        return ""
    return trim_sentence(item, max_len=240)


def _parse_business_line(line: str) -> str:
    if _is_business_label(line):
        return ""
    has_marker = re.match(r"^\s*(?:[-*]|\d+[.)])\s+", line)
    item = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip().strip("-* ")
    if not item or is_promotional(item):
        return ""
    if not has_marker and ":" not in item and "：" not in item:
        return ""
    return trim_sentence(item, max_len=280)


def _is_summary_label(line: str) -> bool:
    return line.strip().strip(":：").lower() in {
        "key points", "summary", "overview", "narrative summary", "摘要", "总结", "總結",
        "要点", "要點", "关键要点", "關鍵要點", "正文摘要", "段落摘要",
    }


def _is_business_label(line: str) -> bool:
    return line.strip().strip(":：").lower() in {
        "business lens", "business takeaways", "business brief", "business implications", "商业视角",
        "商業視角", "商业判断", "商業判斷", "商业要点", "商業要點", "商业启示", "商業啟示",
    }


def _is_editorial_label(line: str) -> bool:
    return line.strip().strip(":：").lower() in {
        "editorial article", "commercial article", "article", "lede", "lead", "nut graf",
        "why it matters", "business briefing", "商业文章", "商業文章", "商业新闻分析",
        "商業新聞分析", "商业分析", "商業分析",
    }


def _clean_summary_paragraph(paragraph: str) -> str:
    paragraph = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", paragraph).strip()
    paragraph = re.sub(r"\s+", " ", paragraph)
    if not paragraph or is_promotional(paragraph) or _is_summary_label(paragraph):
        return ""
    return trim_sentence(paragraph, max_len=520)


def _clean_editorial_paragraph(paragraph: str) -> str:
    paragraph = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", paragraph).strip()
    paragraph = re.sub(r"\s+", " ", paragraph)
    if not paragraph or is_promotional(paragraph) or _is_editorial_label(paragraph):
        return ""
    return trim_sentence(paragraph, max_len=720)


def _parse_numbered_sections(text: str, max_sections: int) -> list[ArticleSection]:
    pattern = re.compile(r"(?m)^\s*(?:###\s*)?(?:\d+[.)、]\s*)?([^\n:：]{2,48})[:：]\s*$")
    matches = list(pattern.finditer(text))
    sections: list[ArticleSection] = []
    for index, match in enumerate(matches[:max_sections]):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = _clean_section_body(text[start:end])
        if body:
            sections.append(ArticleSection(title=_clean_section_title(match.group(1), index + 1), body=body))
    return sections


def _clean_section_title(title: str, index: int) -> str:
    cleaned = re.sub(r"^\s*(?:#+\s*)?(?:\d+[.)、]\s*)?", "", title).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" :-：")
    banned = ("transcript segment", "片段总结", "片段總結", "转录片段", "轉錄片段")
    if not cleaned or any(term in cleaned.lower() for term in banned):
        return f"第 {index} 节"
    if len(cleaned) > 56:
        return cleaned[:55].rstrip() + "..."
    return cleaned


def _clean_section_body(body: str) -> str:
    lines = []
    blank_pending = False
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            blank_pending = bool(lines)
            continue
        if is_promotional(line):
            continue
        if blank_pending and lines and lines[-1] != "":
            lines.append("")
        lines.append(line)
        blank_pending = False
    return "\n".join(lines).strip()
