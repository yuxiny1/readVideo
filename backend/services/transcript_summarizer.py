import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SummaryWindow:
    text: str
    start: int
    end: int


@dataclass(frozen=True)
class ArticleSection:
    title: str
    body: str


@dataclass(frozen=True)
class ArticleNote:
    summary_items: list[str]
    sections: list[ArticleSection]
    summary_paragraphs: list[str] = field(default_factory=list)


PROMOTIONAL_PATTERNS = (
    "hello",
    "大家好",
    "訂閱",
    "按讚",
    "點個",
    "資訊欄",
    "影片底下",
    "追蹤我的",
    "Telegram",
    "IG",
    "follow",
    "下次見",
)

TOPIC_GROUPS = (
    ("市場背景", ("股市", "市場", "創新高", "宏觀", "台股", "美股", "NASDAQ", "SMP500")),
    ("美元體系", ("美元不再", "美元就不再", "美元霸權", "美元體系", "美元", "黃金窗口", "黃金本位", "美債", "1971")),
    ("石油美元", ("石油美元", "petrodollar", "石油", "沙烏地", "Saudi", "OPEC", "opac", "美債")),
    ("去美元化", ("去美元化", "外匯儲備量", "美元儲備", "央行", "人民幣", "swap lines", "拋售", "凍結")),
    ("投資策略", ("充足的現金", "現金倉位", "投資上面", "投資", "現金", "黃金", "比特幣", "股票", "ETF", "風險")),
    ("AI 與产业", ("AI 的產業", "AI 产业", "AI 產業", "AI 的能源", "半導體", "NVIDIA", "台積電", "PanTier", "Palantir", "特斯拉", "QQQ", "VOO")),
    ("白领工作的本质", ("白领工作", "白領工作", "knowledge worker", "知识工作者", "知識工作者", "认知中介", "認知中介")),
    ("工作价值", ("bullshit jobs", "bullshit", "狗屁工作", "没有意义", "沒有意義", "成就感", "价值感", "價值感")),
    ("生产力变化", ("生产力", "生產力", "生产关系", "生產關係", "范式", "範式", "自动化", "自動化", "AI")),
    ("个人应对", ("结果负责", "結果負責", "行动点", "行動點", "作品集", "定义问题", "定義問題", "信任", "整合者", "contractor", "business owner")),
)


def summarize_transcript(transcript_text: str, max_items: int = 6) -> list[str]:
    lines = _content_lines(transcript_text)
    if not lines:
        return []

    windows = _summary_windows(lines)
    if not windows:
        return [_trim_sentence(line) for line in lines[:max_items]]

    selected: list[str] = []
    used_line_numbers: set[int] = set()

    for label, keywords in TOPIC_GROUPS:
        window = _best_topic_window(windows, keywords, used_line_numbers)
        if window is None:
            continue

        selected.append(f"{label}: {_trim_sentence(window.text)}")
        used_line_numbers.update(range(window.start, window.end + 1))
        if len(selected) >= max_items:
            return selected

    if len(selected) >= min(4, max_items):
        return selected

    for window in _ranked_windows(windows, used_line_numbers):
        item = _trim_sentence(window.text)
        if _is_duplicate_summary(item, selected):
            continue
        selected.append(item)
        used_line_numbers.update(range(window.start, window.end + 1))
        if len(selected) >= max_items:
            break

    return selected


def summarize_transcript_with_backend(
    transcript_text: str,
    backend: str = "extractive",
    ollama_model: str = "qwen2.5:32b",
    ollama_url: str = "http://127.0.0.1:11434/api/generate",
) -> list[str]:
    if backend == "extractive":
        return summarize_transcript(transcript_text)
    if backend == "ollama":
        return summarize_transcript_with_ollama(transcript_text, ollama_model, ollama_url)
    raise RuntimeError("summary_backend must be extractive or ollama.")


def summarize_transcript_with_ollama(
    transcript_text: str,
    model: str = "qwen2.5:32b",
    url: str = "http://127.0.0.1:11434/api/generate",
    timeout_seconds: int = 180,
    max_items: int = 8,
    chunk_chars: int = 7000,
) -> list[str]:
    chunks = _prompt_chunks(transcript_text, max_chars=chunk_chars)
    if not chunks:
        return []

    if len(chunks) == 1:
        prompt = _final_summary_prompt(chunks[0], max_items)
        items = _request_ollama_summary(prompt, model, url, timeout_seconds)
        if not items:
            raise RuntimeError("Ollama summary did not return usable bullet points.")
        return items[:max_items]

    chunk_notes: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        prompt = _chunk_summary_prompt(chunk, index, len(chunks))
        chunk_notes.extend(_request_ollama_summary(prompt, model, url, timeout_seconds))

    if not chunk_notes:
        raise RuntimeError("Ollama summary did not return usable bullet points.")

    prompt = _final_summary_prompt("\n".join(f"- {item}" for item in chunk_notes), max_items)
    items = _request_ollama_summary(prompt, model, url, timeout_seconds)
    if not items:
        return chunk_notes[:max_items]
    return items[:max_items]


def build_article_note_with_ollama(
    transcript_text: str,
    model: str = "qwen2.5:32b",
    url: str = "http://127.0.0.1:11434/api/generate",
    timeout_seconds: int = 240,
    max_summary_items: int = 7,
    max_sections: int = 10,
    chunk_chars: int = 5200,
) -> ArticleNote:
    chunks = _prompt_chunks(transcript_text, max_chars=chunk_chars)
    if not chunks:
        return ArticleNote(summary_items=[], sections=[], summary_paragraphs=[])

    if len(chunks) == 1:
        prompt = _article_note_prompt(chunks[0], max_summary_items, max_sections)
        return _parse_article_note(
            _request_ollama_text(prompt, model, url, timeout_seconds),
            max_summary_items=max_summary_items,
            max_sections=max_sections,
        )

    chunk_notes: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        prompt = _chunk_article_prompt(chunk, index, len(chunks))
        note = _request_ollama_text(prompt, model, url, timeout_seconds)
        if note.strip():
            chunk_notes.append(f"Chunk {index}/{len(chunks)}\n{note.strip()}")

    if not chunk_notes:
        raise RuntimeError("Ollama note generation did not return usable chunk notes.")

    prompt = _article_note_prompt("\n\n".join(chunk_notes), max_summary_items, max_sections)
    article = _parse_article_note(
        _request_ollama_text(prompt, model, url, timeout_seconds),
        max_summary_items=max_summary_items,
        max_sections=max_sections,
    )
    if article.summary_items or article.sections:
        return article

    fallback_summary = _parse_markdown_bullets("\n".join(chunk_notes))[:max_summary_items]
    return ArticleNote(
        summary_items=fallback_summary,
        sections=[],
        summary_paragraphs=_paragraphs_from_summary_items(fallback_summary),
    )


def _request_ollama_summary(prompt: str, model: str, url: str, timeout_seconds: int) -> list[str]:
    text = _request_ollama_text(prompt, model, url, timeout_seconds)
    return _parse_markdown_bullets(text)


def _request_ollama_text(prompt: str, model: str, url: str, timeout_seconds: int) -> str:
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = _read_ollama_error(exc)
        if "not found" in detail.lower() or "pull" in detail.lower():
            raise RuntimeError(
                f'Ollama model "{model}" is not installed. Run: ollama pull {model}'
            ) from exc
        raise RuntimeError(f"Ollama summary failed: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Ollama summary failed. Make sure Ollama is running at {url} and the model is installed: ollama pull {model}"
        ) from exc

    return str(data.get("response", "")).strip()


def _chunk_summary_prompt(chunk: str, index: int, total: int) -> str:
    return (
        "你是一个严谨的视频笔记助手。下面是 YouTube 转录文本的一段。"
        "请输出 4 到 6 条中文 Markdown bullet，保留这一段里的关键事实、观点、例子、数字、因果关系和行动建议。"
        "每条格式为「主题: 具体总结」。只总结文本里明确出现的内容，不要编造，"
        "不要加入广告、订阅提醒或投资建议免责声明。\n\n"
        f"片段 {index}/{total}:\n{chunk}"
    )


def _final_summary_prompt(notes_text: str, max_items: int) -> str:
    return (
        "你是一个视频笔记编辑。请把下面的转录文本或分段笔记合并成一份高质量中文总结。"
        f"输出最多 {max_items} 条 Markdown bullet。每条格式为「主题: 具体总结」。"
        "要求：去重，按逻辑顺序组织，保留具体论点、例子、数字和行动点；"
        "不要泛泛而谈，不要编造，不要加入广告、订阅提醒或免责声明。\n\n"
        f"内容:\n{notes_text}"
    )


def _chunk_article_prompt(chunk: str, index: int, total: int) -> str:
    return (
        "你是一个严谨的视频笔记编辑。下面是完整转录文本中的一个连续片段。"
        "目标不是压缩成短摘要，而是做高保真覆盖笔记，供后续整理成文章式分段。"
        "请先去掉口头禅、重复识别、寒暄、订阅提醒，只保留真正的信息。"
        "输出中文 Markdown：\n"
        "## Coverage Notes\n"
        "- 按原文顺序列出这一片段里的所有独立信息点，不要因为相似就合并到丢失细节。\n"
        "- 每条写 1 到 2 句，尽量保留原文里的对象、动作、时间、数字、例子、对比、因果和转折。\n"
        "- 如果片段里有很多信息，可以写 8 到 16 条，甚至更多；完整性优先于简短。\n\n"
        "## Section Candidates\n"
        "- 写 2 到 5 个可能的章节主题，用于后续分段。\n\n"
        "不要逐字复制大段转录，不要编造，不要只写空泛概括。\n\n"
        f"片段 {index}/{total}:\n{chunk}"
    )


def _article_note_prompt(material: str, max_summary_items: int, max_sections: int) -> str:
    return (
        "你是一个中文长文编辑，要把视频转录整理成一篇清晰、可阅读、信息覆盖充分的文章式笔记。"
        "输入可能是完整转录，也可能是按顺序整理过的片段笔记。"
        "请用完整内容做全局组织，不要只看开头，不要重复同一句话，不要把逐字稿粘贴进笔记。"
        "尤其重要：分段正文要尽可能复原原文真正讲了什么，不能只写抽象概括，不能遗漏独立信息点。\n\n"
        "输出必须严格使用下面的 Markdown 结构：\n"
        "## Summary\n"
        "先写 1 到 2 段正文式总述，每段 2 到 4 句，像文章摘要一样概括原文整体内容、主线和结论。\n"
        "然后写 5 到 "
        f"{max_summary_items} 条 Markdown bullet，每条都是「主题: 具体结论/事实/行动点」。\n\n"
        "## Sections\n"
        f"### 1. 清楚的章节标题\n"
        "每个章节写成详细正文，而不是短摘要：先用 2 到 4 个自然段按原文顺序复原这一段的主要内容，"
        "再视需要加 3 到 8 条 bullet 补充细节。"
        "章节正文必须保留原文里的关键名词、人名、设备名、时间、数字、例子、因果关系、比较和转折。"
        "如果原文在一个章节里连续讲了多个点，都要写进去，不要只留下一个总括句。"
        f"总共输出 3 到 {max_sections} 个章节，按视频逻辑顺序排列。\n\n"
        "章节标题要具体，不要写“Transcript Segment”“片段总结”这种过程词。"
        "如果主题真的不明确，才使用 Section 1、Section 2。"
        "只基于输入内容，不要编造，不要广告，不要免责声明。\n\n"
        f"内容:\n{material}"
    )


def _parse_article_note(text: str, max_summary_items: int = 7, max_sections: int = 8) -> ArticleNote:
    summary_items: list[str] = []
    summary_paragraphs: list[str] = []
    summary_paragraph_lines: list[str] = []
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

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            if mode == "summary":
                flush_summary_paragraph()
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
                flush_section()
                mode = "summary"
                continue
            if mode == "summary" and any(word in heading_lower for word in ("key points", "要点", "要點", "重点", "重點")):
                flush_summary_paragraph()
                continue
            if any(word in heading_lower for word in ("section", "sections", "章节", "章節", "分段", "正文", "笔记", "筆記")) and heading_match.group(1) in {"#", "##"}:
                flush_summary_paragraph()
                flush_section()
                mode = "sections"
                continue
            if mode == "sections" or heading_match.group(1) in {"###", "####"}:
                flush_summary_paragraph()
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

        if mode == "sections":
            current_body.append(stripped)
            continue

        item = _parse_summary_line(stripped)
        if item and len(summary_items) < max_summary_items:
            summary_items.append(item)

    flush_summary_paragraph()
    flush_section()
    if not sections:
        sections = _parse_numbered_sections(text, max_sections)

    summary_items = _dedupe_items(summary_items)[:max_summary_items]
    summary_paragraphs = _dedupe_paragraphs(summary_paragraphs) or _paragraphs_from_summary_items(summary_items)
    return ArticleNote(
        summary_items=summary_items,
        sections=sections[:max_sections],
        summary_paragraphs=summary_paragraphs[:2],
    )


def _parse_summary_line(line: str) -> str:
    has_marker = re.match(r"^\s*(?:[-*]|\d+[.)])\s+", line)
    item = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
    item = item.strip("-* ")
    if not item or _is_promotional(item):
        return ""
    if not has_marker and ":" not in item and "：" not in item:
        return ""
    return _trim_sentence(item, max_len=240)


def _is_summary_label(line: str) -> bool:
    normalized = line.strip().strip(":：").lower()
    return normalized in {
        "key points",
        "summary",
        "overview",
        "narrative summary",
        "摘要",
        "总结",
        "總結",
        "要点",
        "要點",
        "关键要点",
        "關鍵要點",
        "正文摘要",
        "段落摘要",
    }


def _clean_summary_paragraph(paragraph: str) -> str:
    paragraph = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", paragraph).strip()
    paragraph = re.sub(r"\s+", " ", paragraph)
    if not paragraph or _is_promotional(paragraph) or _is_summary_label(paragraph):
        return ""
    return _trim_sentence(paragraph, max_len=520)


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
    lower_cleaned = cleaned.lower()
    banned = ("transcript segment", "片段总结", "片段總結", "转录片段", "轉錄片段")
    if not cleaned or any(term in lower_cleaned for term in banned):
        return f"Section {index}"
    if len(cleaned) > 56:
        cleaned = cleaned[:55].rstrip() + "..."
    return cleaned


def _clean_section_body(body: str) -> str:
    lines = []
    blank_pending = False
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            blank_pending = bool(lines)
            continue
        if _is_promotional(line):
            continue
        if blank_pending and lines and lines[-1] != "":
            lines.append("")
        lines.append(line)
        blank_pending = False
    return "\n".join(lines).strip()


def _dedupe_items(items: list[str]) -> list[str]:
    selected: list[str] = []
    for item in items:
        if item and not _is_duplicate_summary(item, selected):
            selected.append(item)
    return selected


def _dedupe_paragraphs(paragraphs: list[str]) -> list[str]:
    selected: list[str] = []
    for paragraph in paragraphs:
        if paragraph and not _is_duplicate_summary(paragraph, selected):
            selected.append(paragraph)
    return selected


def _paragraphs_from_summary_items(items: list[str], max_items: int = 5) -> list[str]:
    selected = [_strip_summary_label(item) for item in items[:max_items] if item]
    if not selected:
        return []
    paragraph = "；".join(selected).rstrip("。；") + "。"
    return [_trim_sentence(paragraph, max_len=520)]


def _strip_summary_label(item: str) -> str:
    return re.sub(r"^[^:：]{2,18}[:：]\s*", "", item).strip()


def _tokens(sentence: str) -> list[str]:
    ascii_words = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", sentence.lower())
    chinese_words = re.findall(r"[\u4e00-\u9fff]{2,4}", sentence)
    return ascii_words + chinese_words


def _read_ollama_error(exc: urllib.error.HTTPError) -> str:
    try:
        data = json.loads(exc.read().decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return exc.reason or "Unknown Ollama HTTP error"
    return str(data.get("error") or exc.reason or "Unknown Ollama HTTP error")


def _trim_sentence(sentence: str, max_len: int = 190) -> str:
    sentence = sentence.strip()
    if len(sentence) <= max_len:
        return sentence
    return sentence[: max_len - 1].rstrip() + "..."


def _content_lines(transcript_text: str) -> list[str]:
    lines = []
    for line in transcript_text.splitlines():
        cleaned = _normalize_text(line)
        if not cleaned or _is_promotional(cleaned):
            continue
        lines.append(cleaned)
    return lines


def _prompt_chunks(transcript_text: str, max_chars: int = 7000) -> list[str]:
    lines = _content_lines(transcript_text)
    chunks = []
    current = []
    current_len = 0

    for line in lines:
        if current and current_len + len(line) + 1 > max_chars:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += len(line) + 1

    if current:
        chunks.append("\n".join(current))

    return chunks


def _parse_markdown_bullets(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        has_marker = re.match(r"^\s*(?:[-*]|\d+[.)])\s+", line)
        item = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
        item = item.strip("-* ")
        if not has_marker and ":" not in item and "：" not in item:
            continue
        if item and not _is_promotional(item):
            items.append(_trim_sentence(item, max_len=220))
    return items


def _summary_windows(lines: list[str], max_lines: int = 4, min_chars: int = 12, max_chars: int = 260) -> list[SummaryWindow]:
    windows: list[SummaryWindow] = []
    for start in range(len(lines)):
        fragments = []
        for end in range(start, min(start + max_lines, len(lines))):
            fragments.append(lines[end])
            text = _normalize_text(" ".join(fragments))
            if len(text) > max_chars:
                break
            if len(text) >= min_chars:
                windows.append(SummaryWindow(text=text, start=start, end=end))
    return windows


def _best_topic_window(
    windows: list[SummaryWindow],
    keywords: tuple[str, ...],
    used_line_numbers: set[int],
) -> Optional[SummaryWindow]:
    best_score = 0.0
    best_window = None
    for window in windows:
        if _overlaps_used_lines(window, used_line_numbers):
            continue
        keyword_score = _keyword_score(window.text, keywords)
        if keyword_score == 0:
            continue

        score = keyword_score * 8
        score += min(len(window.text), 140) / 60
        score += 1 / (window.start + 1)
        score -= (window.end - window.start) * 3
        score -= _competing_topic_penalty(window.text, keywords)
        score += _primary_keyword_bonus(window.text, keywords)
        if len(window.text) < 45:
            score -= 1.5

        if score > best_score:
            best_score = score
            best_window = window

    return best_window


def _ranked_windows(windows: list[SummaryWindow], used_line_numbers: set[int]) -> list[SummaryWindow]:
    broad_keywords = tuple(keyword for _, keywords in TOPIC_GROUPS for keyword in keywords)
    scored = []
    for window in windows:
        if _overlaps_used_lines(window, used_line_numbers):
            continue
        score = _keyword_score(window.text, broad_keywords) * 4
        score += len(set(_tokens(window.text))) * 0.3
        score += min(len(window.text), 140) / 80
        score -= window.start * 0.002
        scored.append((score, window.start, window))

    scored.sort(key=lambda item: (-item[0], item[1]))
    return [window for _, _, window in scored]


def section_title(section: str, index: Optional[int] = None) -> str:
    best_label = ""
    best_score = 0
    second_score = 0
    for label, keywords in TOPIC_GROUPS:
        score = _keyword_score(section, keywords)
        if score > best_score:
            second_score = best_score
            best_score = score
            best_label = label
        elif score > second_score:
            second_score = score

    fallback = f"Section {index}" if index is not None else "Section"
    if best_score < 5 or best_score - second_score < 2:
        return fallback
    return best_label


def _keyword_score(text: str, keywords: tuple[str, ...]) -> int:
    lower_text = text.lower()
    score = 0
    for keyword in keywords:
        keyword_lower = keyword.lower()
        count = lower_text.count(keyword_lower)
        if count:
            score += count * (3 if len(keyword_lower) >= 4 else 1)
    return score


def _competing_topic_penalty(text: str, current_keywords: tuple[str, ...]) -> int:
    lower_text = text.lower()
    current_primary = {keyword.lower() for keyword in current_keywords[:3]}
    penalty = 0
    for _, topic_keywords in TOPIC_GROUPS:
        if topic_keywords == current_keywords:
            continue
        for keyword in topic_keywords[:3]:
            keyword_lower = keyword.lower()
            if keyword_lower not in current_primary and keyword_lower in lower_text:
                penalty += 18
                break
    return penalty


def _primary_keyword_bonus(text: str, keywords: tuple[str, ...]) -> int:
    lower_text = text.lower()
    for bonus, keyword in zip((70, 35, 25), keywords[:3]):
        if keyword.lower() in lower_text:
            return bonus
    return 0


def _overlaps_used_lines(window: SummaryWindow, used_line_numbers: set[int], padding: int = 0) -> bool:
    return any(line_number in used_line_numbers for line_number in range(window.start - padding, window.end + padding + 1))


def _is_duplicate_summary(candidate: str, selected: list[str]) -> bool:
    candidate_key = _dedupe_key(candidate)
    candidate_tokens = set(_tokens(candidate))
    for item in selected:
        item_key = _dedupe_key(item)
        if candidate_key in item_key or item_key in candidate_key:
            return True

        item_tokens = set(_tokens(item))
        shared_tokens = candidate_tokens & item_tokens
        overlap_threshold = max(4, int(min(len(candidate_tokens), len(item_tokens)) * 0.35))
        if len(shared_tokens) >= overlap_threshold:
            return True

    return False


def _dedupe_key(value: str) -> str:
    return re.sub(r"\W+", "", value.lower())


def _is_promotional(text: str) -> bool:
    lower_text = text.lower()
    return any(pattern.lower() in lower_text for pattern in PROMOTIONAL_PATTERNS)


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
