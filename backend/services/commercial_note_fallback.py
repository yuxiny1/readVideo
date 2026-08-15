import re
from typing import Iterable

from backend.services.note_models import ArticleSection


def fallback_business_lens(
    video_title: str,
    summary_items: Iterable[str],
    summary_paragraphs: Iterable[str],
    sections: Iterable[ArticleSection],
) -> list[str]:
    items = [item.strip() for item in summary_items if item.strip()]
    paragraphs = [paragraph.strip() for paragraph in summary_paragraphs if paragraph.strip()]
    section_list = list(sections)
    lens: list[str] = []

    if items:
        lens.append(f"商业核心: {_strip_summary_label(items[0])}")
    elif paragraphs:
        lens.append(f"商业核心: {_trim_paragraph(paragraphs[0], max_len=260)}")
    else:
        lens.append(f"商业核心: {video_title} 主要提供知识或背景信息，原文没有直接给出商业行动。")

    if len(items) > 1:
        lens.append(f"为什么重要: {_strip_summary_label(items[1])}")
    elif section_list:
        lens.append(f"为什么重要: {section_list[0].title} 是理解后续判断的入口。")

    for label, section in zip(("风险", "机会", "下一步信号"), section_list[:3]):
        body = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", section.body.strip())
        body = re.sub(r"\s+", " ", body)
        if body:
            lens.append(f"{label}: {_trim_paragraph(body, max_len=260)}")

    return [_trim_paragraph(item, max_len=280) for item in lens if item][:7]


def fallback_editorial_paragraphs(
    video_title: str,
    summary_items: Iterable[str],
    summary_paragraphs: Iterable[str],
    sections: Iterable[ArticleSection],
) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in summary_paragraphs if paragraph.strip()]
    section_list = list(sections)
    if not paragraphs and summary_items:
        stripped_items = [
            re.sub(r"^[^:：]{2,18}[:：]\s*", "", item).strip()
            for item in summary_items
            if item.strip()
        ]
        stripped_items = [item for item in stripped_items if item]
        if stripped_items:
            paragraphs.append(f"{video_title} 的核心并不只是几条结论，而是一组需要放在商业语境里理解的变化。{stripped_items[0]}")

    for section in section_list[:4]:
        body = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", section.body.strip())
        body = re.sub(r"\s+", " ", body)
        if body:
            paragraphs.append(f"在“{section.title}”这一部分，视频把问题推进到更具体的层面：{body}")

    return [_trim_paragraph(paragraph) for paragraph in paragraphs if paragraph][:8]


def _trim_paragraph(paragraph: str, max_len: int = 720) -> str:
    paragraph = paragraph.strip()
    if len(paragraph) <= max_len:
        return paragraph
    return paragraph[: max_len - 1].rstrip() + "..."


def _strip_summary_label(item: str) -> str:
    return re.sub(r"^[^:：]{2,18}[:：]\s*", "", item).strip()
