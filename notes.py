import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class NoteResult:
    markdown_path: str
    summary: str
    section_count: int
    summary_backend: str = "extractive"


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
) -> list[str]:
    prompt = (
        "你是一个视频笔记助手。请根据下面的 YouTube 转录文本，输出 6 条中文 Markdown bullet。"
        "每条格式为「主题: 一句话总结」。只总结文本里明确出现的内容，不要编造，"
        "不要加入广告、订阅提醒或投资建议免责声明。\n\n"
        f"转录文本:\n{_prompt_excerpt(transcript_text)}"
    )
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
    items = _parse_markdown_bullets(text)
    if not items:
        raise RuntimeError("Ollama summary did not return usable bullet points.")
    return items[:6]


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
        lines.extend([f"### {index}. {_section_title(section)}", "", section, ""])

    lines.extend(["## Full Transcript", "", transcript_text.strip(), ""])
    return "\n".join(lines)


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[\\/:*?\"<>|]+", "-", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:180] or "readvideo-note"


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


def _prompt_excerpt(transcript_text: str, max_chars: int = 9000) -> str:
    lines = _content_lines(transcript_text)
    text = "\n".join(lines)
    if len(text) <= max_chars:
        return text

    head = text[: max_chars // 3]
    middle_start = max(0, len(text) // 2 - max_chars // 6)
    middle = text[middle_start : middle_start + max_chars // 3]
    tail = text[-max_chars // 3 :]
    return "\n...\n".join([head, middle, tail])


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


def _section_title(section: str) -> str:
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
