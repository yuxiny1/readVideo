import re


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


def content_lines(transcript_text: str) -> list[str]:
    lines = []
    for line in transcript_text.splitlines():
        cleaned = normalize_text(line)
        if cleaned and not is_promotional(cleaned):
            lines.append(cleaned)
    return lines


def prompt_chunks(transcript_text: str, max_chars: int = 7000) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in content_lines(transcript_text):
        if current and current_len + len(line) + 1 > max_chars:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += len(line) + 1
    if current:
        chunks.append("\n".join(current))
    return chunks


def parse_markdown_bullets(text: str) -> list[str]:
    items = []
    for line in text.splitlines():
        has_marker = re.match(r"^\s*(?:[-*]|\d+[.)])\s+", line)
        item = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip().strip("-* ")
        if not has_marker and ":" not in item and "：" not in item:
            continue
        if item and not is_promotional(item):
            items.append(trim_sentence(item, max_len=220))
    return items


def dedupe_items(items: list[str]) -> list[str]:
    selected: list[str] = []
    for item in items:
        if item and not is_duplicate(item, selected):
            selected.append(item)
    return selected


def dedupe_paragraphs(paragraphs: list[str]) -> list[str]:
    selected: list[str] = []
    for paragraph in paragraphs:
        if paragraph and not is_duplicate(paragraph, selected):
            selected.append(paragraph)
    return selected


def paragraphs_from_summary_items(items: list[str], max_items: int = 5) -> list[str]:
    selected = [strip_summary_label(item) for item in items[:max_items] if item]
    if not selected:
        return []
    paragraph = "；".join(selected).rstrip("。；") + "。"
    return [trim_sentence(paragraph, max_len=520)]


def strip_summary_label(item: str) -> str:
    return re.sub(r"^[^:：]{2,18}[:：]\s*", "", item).strip()


def tokens(sentence: str) -> list[str]:
    ascii_words = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", sentence.lower())
    chinese_words = re.findall(r"[\u4e00-\u9fff]{2,4}", sentence)
    return ascii_words + chinese_words


def trim_sentence(sentence: str, max_len: int = 190) -> str:
    sentence = sentence.strip()
    if len(sentence) <= max_len:
        return sentence
    return sentence[: max_len - 1].rstrip() + "..."


def is_duplicate(candidate: str, selected: list[str]) -> bool:
    candidate_key = _dedupe_key(candidate)
    candidate_tokens = set(tokens(candidate))
    for item in selected:
        item_key = _dedupe_key(item)
        if candidate_key in item_key or item_key in candidate_key:
            return True
        item_tokens = set(tokens(item))
        overlap_threshold = max(4, int(min(len(candidate_tokens), len(item_tokens)) * 0.35))
        if len(candidate_tokens & item_tokens) >= overlap_threshold:
            return True
    return False


def is_promotional(text: str) -> bool:
    lower_text = text.lower()
    return any(pattern.lower() in lower_text for pattern in PROMOTIONAL_PATTERNS)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _dedupe_key(value: str) -> str:
    return re.sub(r"\W+", "", value.lower())
