from dataclasses import dataclass
from typing import Optional

from backend.services.transcript_text import content_lines, is_duplicate, normalize_text, tokens, trim_sentence


@dataclass(frozen=True)
class SummaryWindow:
    text: str
    start: int
    end: int


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
    lines = content_lines(transcript_text)
    if not lines:
        return []
    windows = _summary_windows(lines)
    if not windows:
        return [trim_sentence(line) for line in lines[:max_items]]

    selected: list[str] = []
    used_line_numbers: set[int] = set()
    for label, keywords in TOPIC_GROUPS:
        window = _best_topic_window(windows, keywords, used_line_numbers)
        if window is None:
            continue
        selected.append(f"{label}: {trim_sentence(window.text)}")
        used_line_numbers.update(range(window.start, window.end + 1))
        if len(selected) >= max_items:
            return selected

    if len(selected) >= min(4, max_items):
        return selected
    for window in _ranked_windows(windows, used_line_numbers):
        item = trim_sentence(window.text)
        if is_duplicate(item, selected):
            continue
        selected.append(item)
        used_line_numbers.update(range(window.start, window.end + 1))
        if len(selected) >= max_items:
            break
    return selected


def section_title(section: str, index: Optional[int] = None) -> str:
    best_label = ""
    best_score = 0
    second_score = 0
    for label, keywords in TOPIC_GROUPS:
        score = _keyword_score(section, keywords)
        if score > best_score:
            second_score, best_score, best_label = best_score, score, label
        elif score > second_score:
            second_score = score
    fallback = f"第 {index} 节" if index is not None else "未命名章节"
    if best_score < 5 or best_score - second_score < 2:
        return fallback
    return best_label


def _summary_windows(
    lines: list[str],
    max_lines: int = 4,
    min_chars: int = 12,
    max_chars: int = 260,
) -> list[SummaryWindow]:
    windows: list[SummaryWindow] = []
    for start in range(len(lines)):
        fragments = []
        for end in range(start, min(start + max_lines, len(lines))):
            fragments.append(lines[end])
            text = normalize_text(" ".join(fragments))
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
            best_score, best_window = score, window
    return best_window


def _ranked_windows(windows: list[SummaryWindow], used_line_numbers: set[int]) -> list[SummaryWindow]:
    broad_keywords = tuple(keyword for _, keywords in TOPIC_GROUPS for keyword in keywords)
    scored = []
    for window in windows:
        if _overlaps_used_lines(window, used_line_numbers):
            continue
        score = _keyword_score(window.text, broad_keywords) * 4
        score += len(set(tokens(window.text))) * 0.3
        score += min(len(window.text), 140) / 80
        score -= window.start * 0.002
        scored.append((score, window.start, window))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [window for _, _, window in scored]


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


def _overlaps_used_lines(window: SummaryWindow, used_line_numbers: set[int]) -> bool:
    return any(line_number in used_line_numbers for line_number in range(window.start, window.end + 1))
