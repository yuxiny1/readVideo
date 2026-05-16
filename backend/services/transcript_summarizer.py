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


def _request_ollama_summary(prompt: str, model: str, url: str, timeout_seconds: int) -> list[str]:
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
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(
            f"Ollama summary failed. Make sure Ollama is running and the model is installed: ollama pull {model}"
        ) from exc

    text = str(data.get("response", "")).strip()
    return _parse_markdown_bullets(text)


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
