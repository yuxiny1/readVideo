import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SummaryWindow:
    text: str
    start: int
    end: int


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
    ("美伊冲突", ("特朗普", "伊朗", "战争", "霍尔木兹", "核能力", "导弹", "军事基地", "Iran", "Hormuz")),
    ("中国影响力", ("中国", "亞洲", "亚洲", "tribute", "贡赋", "朝贡", "人民币", "世界秩序", "机器人", "生活水平")),
    ("世界秩序变化", ("世界秩序", "二战后", "美国主导", "赢家", "输家", "中立国", "大国", "影响力", "秩序")),
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
    ollama_model: str = "qwen2.5:3b",
    ollama_url: str = "http://127.0.0.1:11434/api/generate",
) -> list[str]:
    if backend == "extractive":
        return summarize_transcript(transcript_text)
    if backend == "ollama":
        return summarize_transcript_with_ollama(transcript_text, ollama_model, ollama_url)
    raise RuntimeError("summary_backend must be extractive or ollama.")


def build_editorial_article_with_backend(
    transcript_text: str,
    summary_items: list[str],
    section_notes: list[tuple[str, str, tuple[str, ...]]],
    backend: str = "extractive",
    ollama_model: str = "qwen2.5:3b",
    ollama_url: str = "http://127.0.0.1:11434/api/generate",
) -> list[str]:
    if backend == "ollama":
        return build_editorial_article_with_ollama(
            transcript_text,
            summary_items,
            section_notes,
            model=ollama_model,
            url=ollama_url,
        )
    if backend == "extractive":
        return build_editorial_article_fallback(summary_items, section_notes)
    raise RuntimeError("summary_backend must be extractive or ollama.")


def summarize_transcript_with_ollama(
    transcript_text: str,
    model: str = "qwen2.5:3b",
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


def build_editorial_article_with_ollama(
    transcript_text: str,
    summary_items: list[str],
    section_notes: list[tuple[str, str, tuple[str, ...]]],
    model: str = "qwen2.5:3b",
    url: str = "http://127.0.0.1:11434/api/generate",
    timeout_seconds: int = 240,
    chunk_chars: int = 7000,
) -> list[str]:
    chunks = _prompt_chunks(transcript_text, max_chars=chunk_chars)
    if not chunks:
        return build_editorial_article_fallback(summary_items, section_notes)

    source_text = _editorial_source_text(summary_items, section_notes)
    if len(chunks) == 1:
        prompt = _editorial_article_prompt(source_text, chunks[0])
        article_text = _request_ollama_text(prompt, model, url, timeout_seconds, temperature=0.35)
        paragraphs = _parse_editorial_paragraphs(article_text)
        return paragraphs or build_editorial_article_fallback(summary_items, section_notes)

    chunk_briefs: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        prompt = _editorial_chunk_prompt(chunk, index, len(chunks))
        chunk_briefs.extend(_request_ollama_summary(prompt, model, url, timeout_seconds))

    combined_context = "\n".join(f"- {item}" for item in chunk_briefs) or source_text
    prompt = _editorial_article_prompt(source_text, combined_context)
    article_text = _request_ollama_text(prompt, model, url, timeout_seconds, temperature=0.35)
    paragraphs = _parse_editorial_paragraphs(article_text)
    return paragraphs or build_editorial_article_fallback(summary_items, section_notes)


def build_editorial_article_fallback(
    summary_items: list[str],
    section_notes: list[tuple[str, str, tuple[str, ...]]],
) -> list[str]:
    facts = [_strip_topic(item) for item in summary_items if item.strip()]
    section_titles = [title for title, _, _ in section_notes if title and title != "Transcript Segment"]
    first_fact = facts[0] if facts else "这支视频围绕一个正在形成的商业与政策议题展开"
    second_fact = facts[1] if len(facts) > 1 else ""

    paragraphs = [
        f"这支视频的核心并不是单一事件本身，而是它背后正在改变的商业环境。{first_fact}",
    ]
    if second_fact:
        paragraphs.append(f"更值得注意的是，视频把短期新闻放进了更长的周期中观察。{second_fact}")

    if section_titles:
        topic_list = "、".join(dict.fromkeys(section_titles[:4]))
        paragraphs.append(f"从结构上看，讨论集中在 {topic_list} 等几个层面，重点不是制造情绪，而是解释这些变量如何互相影响。")

    remaining = facts[2:5]
    if remaining:
        paragraphs.append("对读者来说，最有价值的部分在于几个可跟踪的判断：" + "；".join(remaining) + "。")

    paragraphs.append(
        "这类内容更适合被当作一份背景材料来读：先抓住主线，再回到分段原文核对细节。真正的结论不只在摘要里，也藏在说话人如何排列事实、风险和时间顺序之中。"
    )
    return [_trim_sentence(paragraph, max_len=520) for paragraph in paragraphs if paragraph.strip()]


def _request_ollama_summary(prompt: str, model: str, url: str, timeout_seconds: int) -> list[str]:
    text = _request_ollama_text(prompt, model, url, timeout_seconds, temperature=0.2)
    return _parse_markdown_bullets(text)


def _request_ollama_text(
    prompt: str,
    model: str,
    url: str,
    timeout_seconds: int,
    temperature: float = 0.2,
) -> str:
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
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
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Ollama summary failed. Make sure Ollama is running and the model is installed: ollama pull {model}"
        ) from exc

    return str(data.get("response", "")).strip()


def _editorial_chunk_prompt(chunk: str, index: int, total: int) -> str:
    return (
        "你是一个商业新闻编辑。下面是长视频转录文本的一段。"
        "请输出 5 到 8 条中文 Markdown bullet，提炼这一段中可以用于商业分析文章的事实、数字、因果关系、人物观点和风险。"
        "不要写成普通摘要，不要加入文本中没有的背景，不要模仿任何特定媒体的固定措辞。\n\n"
        f"片段 {index}/{total}:\n{chunk}"
    )


def _editorial_article_prompt(source_text: str, transcript_or_brief: str) -> str:
    return (
        "你是一名资深商业新闻编辑，要把 YouTube 转录内容改写成中文商业分析式文章摘要。"
        "风格要求：像严肃商业报刊的解释型文章，有清晰的 lede、背景、利害关系、转折和影响；"
        "语气克制、具体、有判断，但不要夸张，不要空泛，不要模仿或复制任何特定媒体的专有文风、标题套路或固定句式。"
        "输出要求：只输出 5 到 8 个自然段；不要 Markdown bullet；不要编造转录里没有的事实；"
        "如果原文信息不足，请明确保持谨慎。每段 60 到 140 个中文字符，适合忙碌的商业读者快速阅读。\n\n"
        f"已有结构化要点:\n{source_text}\n\n"
        f"转录文本或分段简报:\n{transcript_or_brief}"
    )


def _editorial_source_text(
    summary_items: list[str],
    section_notes: list[tuple[str, str, tuple[str, ...]]],
) -> str:
    lines = ["Summary:"]
    lines.extend(f"- {item}" for item in summary_items)
    lines.append("")
    lines.append("Sections:")
    for title, text, notes in section_notes:
        lines.append(f"- {title}: {'; '.join(notes) if notes else _trim_sentence(text, max_len=160)}")
    return "\n".join(lines)


def _parse_editorial_paragraphs(text: str) -> list[str]:
    paragraphs = []
    current = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                paragraphs.append(_clean_editorial_paragraph(" ".join(current)))
                current = []
            continue
        if re.match(r"^#{1,6}\s+", line):
            continue
        has_marker = re.match(r"^\s*(?:[-*]|\d+[.)])\s*", line)
        if has_marker and current:
            paragraphs.append(_clean_editorial_paragraph(" ".join(current)))
            current = []
        line = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
        if line:
            current.append(line)

    if current:
        paragraphs.append(_clean_editorial_paragraph(" ".join(current)))

    return [paragraph for paragraph in paragraphs if paragraph and not _is_promotional(paragraph)][:8]


def _clean_editorial_paragraph(paragraph: str) -> str:
    paragraph = re.sub(r"\s+", " ", paragraph).strip()
    paragraph = paragraph.strip("-* ")
    return paragraph


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


def _tokens(sentence: str) -> list[str]:
    ascii_words = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", sentence.lower())
    chinese_words = re.findall(r"[\u4e00-\u9fff]{2,4}", sentence)
    return ascii_words + chinese_words


def _trim_sentence(sentence: str, max_len: int = 190) -> str:
    sentence = sentence.strip()
    if len(sentence) <= max_len:
        return sentence
    return sentence[: max_len - 1].rstrip() + "..."


def _strip_topic(item: str) -> str:
    item = item.strip()
    if ":" in item:
        return item.split(":", 1)[1].strip()
    if "：" in item:
        return item.split("：", 1)[1].strip()
    return item


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


def section_title(section: str) -> str:
    best_label = "Transcript Segment"
    best_score = 0
    for label, keywords in TOPIC_GROUPS:
        score = _keyword_score(section, keywords)
        if score > best_score:
            best_score = score
            best_label = label
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
