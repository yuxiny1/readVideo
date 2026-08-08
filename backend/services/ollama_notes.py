from backend.services.article_note_parser import parse_article_note
from backend.services.note_models import ArticleNote
from backend.services.ollama_client import OllamaClient
from backend.services.transcript_text import parse_markdown_bullets, paragraphs_from_summary_items, prompt_chunks


def summarize_transcript_with_ollama(
    transcript_text: str,
    model: str = "qwen3.6:35b",
    url: str = "http://127.0.0.1:11434/api/generate",
    timeout_seconds: int = 180,
    max_items: int = 8,
    chunk_chars: int = 7000,
) -> list[str]:
    chunks = prompt_chunks(transcript_text, max_chars=chunk_chars)
    if not chunks:
        return []
    client = OllamaClient(model, url, timeout_seconds)
    if len(chunks) == 1:
        items = _generate_summary(client, _final_summary_prompt(chunks[0], max_items))
        if not items:
            raise RuntimeError("Ollama 没有返回可用的总结要点。")
        return items[:max_items]

    chunk_notes: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        chunk_notes.extend(_generate_summary(client, _chunk_summary_prompt(chunk, index, len(chunks))))
    if not chunk_notes:
        raise RuntimeError("Ollama 没有返回可用的总结要点。")

    items = _generate_summary(
        client,
        _final_summary_prompt("\n".join(f"- {item}" for item in chunk_notes), max_items),
    )
    return (items or chunk_notes)[:max_items]


def build_article_note_with_ollama(
    transcript_text: str,
    model: str = "qwen3.6:35b",
    url: str = "http://127.0.0.1:11434/api/generate",
    timeout_seconds: int = 240,
    max_summary_items: int = 7,
    max_sections: int = 10,
    chunk_chars: int = 5200,
    note_style: str = "detailed",
) -> ArticleNote:
    chunks = prompt_chunks(transcript_text, max_chars=chunk_chars)
    if not chunks:
        return ArticleNote(summary_items=[], sections=[], summary_paragraphs=[])
    client = OllamaClient(model, url, timeout_seconds)
    if len(chunks) == 1:
        return parse_article_note(
            client.generate(_article_note_prompt(chunks[0], max_summary_items, max_sections, note_style)),
            max_summary_items=max_summary_items,
            max_sections=max_sections,
        )

    chunk_notes: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        note = client.generate(_chunk_article_prompt(chunk, index, len(chunks)))
        if note.strip():
            chunk_notes.append(f"片段 {index}/{len(chunks)}\n{note.strip()}")
    if not chunk_notes:
        raise RuntimeError("Ollama 没有返回可用的分段笔记。")

    article = parse_article_note(
        client.generate(_article_note_prompt("\n\n".join(chunk_notes), max_summary_items, max_sections, note_style)),
        max_summary_items=max_summary_items,
        max_sections=max_sections,
    )
    if article.summary_items or article.sections:
        return article

    fallback_summary = parse_markdown_bullets("\n".join(chunk_notes))[:max_summary_items]
    return ArticleNote(
        summary_items=fallback_summary,
        sections=[],
        summary_paragraphs=paragraphs_from_summary_items(fallback_summary),
        business_items=[],
        editorial_paragraphs=[],
    )


def _generate_summary(client: OllamaClient, prompt: str) -> list[str]:
    return parse_markdown_bullets(client.generate(prompt))


def _chunk_summary_prompt(chunk: str, index: int, total: int) -> str:
    return (
        "你是一个严谨的视频笔记助手。下面是视频转录文本的一段。"
        "请输出 4 到 6 条中文 Markdown 要点，保留这一段里的关键事实、观点、例子、数字、因果关系和行动建议。"
        "每条格式为「主题: 具体总结」。只总结文本里明确出现的内容，不要编造，"
        "不要加入广告、订阅提醒或投资建议免责声明。\n\n"
        f"片段 {index}/{total}:\n{chunk}"
    )


def _final_summary_prompt(notes_text: str, max_items: int) -> str:
    return (
        "你是一个视频笔记编辑。请把下面的转录文本或分段笔记合并成一份高质量中文总结。"
        f"输出最多 {max_items} 条 Markdown 要点。每条格式为「主题：具体总结」。"
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
        "## 覆盖笔记\n"
        "- 按原文顺序列出这一片段里的所有独立信息点，不要因为相似就合并到丢失细节。\n"
        "- 每条写 1 到 2 句，尽量保留原文里的对象、动作、时间、数字、例子、对比、因果和转折。\n"
        "- 如果片段里有很多信息，可以写 8 到 16 条，甚至更多；完整性优先于简短。\n\n"
        "## 章节候选\n"
        "- 写 2 到 5 个可能的章节主题，用于后续分段。\n\n"
        "不要逐字复制大段转录，不要编造，不要只写空泛概括。\n\n"
        f"片段 {index}/{total}:\n{chunk}"
    )


def _article_note_prompt(material: str, max_summary_items: int, max_sections: int, note_style: str) -> str:
    commercial_instruction = ""
    if note_style == "commercial":
        commercial_instruction = (
            "\n## 商业视角\n"
            "先写 4 到 7 条 Markdown 要点，专门提炼商业读者最关心的判断。"
            "每条必须是「主题: 具体判断/事实/风险/机会/指标」，优先使用这些主题："
            "商业核心、为什么重要、风险、机会、关键指标、下一步信号、可执行判断。"
            "必须保留输入里真实出现的公司、产品、市场、数字、时间、人物、因果和不确定性。"
            "如果原文没有商业含义，不要硬编；可以写「商业核心: 原文主要是知识讲解，未直接给出商业行动」。\n\n"
            "\n## 商业分析\n"
            "再写一个 5 到 8 段的商业新闻分析式文章摘要。"
            "这一部分面向忙碌的商业读者：第一段直接说明核心事实，第二段解释其重要性，"
            "后续段落按事实、背景、商业模式/市场结构、风险、机会、影响和下一步信号组织。"
            "要把观点翻译成业务语境：谁受影响、钱/资源/注意力如何流动、哪些假设需要验证、哪些指标值得追踪。"
            "语言要克制、清晰、具备报道感和分析感，像严肃的商业简报，"
            "但不要模仿或复制任何特定媒体的固定表达。"
            "不要使用列表，不要写标题解释，不要泛泛鸡汤，不要投资建议，不要编造。\n"
        )
    return (
        "你是一个中文长文编辑，要把视频转录整理成一篇清晰、可阅读、信息覆盖充分的文章式笔记。"
        "输入可能是完整转录，也可能是按顺序整理过的片段笔记。"
        "请用完整内容做全局组织，不要只看开头，不要重复同一句话，不要把逐字稿粘贴进笔记。"
        "尤其重要：分段正文要尽可能复原原文真正讲了什么，不能只写抽象概括，不能遗漏独立信息点。\n\n"
        "输出必须严格使用下面的 Markdown 结构：\n"
        "## 总结\n"
        "先写 1 到 2 段正文式总述，每段 2 到 4 句，像文章摘要一样概括原文整体内容、主线和结论。\n"
        f"然后写 5 到 {max_summary_items} 条 Markdown 要点，每条都是「主题：具体结论、事实或行动点」。\n\n"
        f"{commercial_instruction}"
        "## 分段笔记\n"
        "### 1. 清楚的章节标题\n"
        "每个章节写成详细正文，而不是短摘要：先用 2 到 4 个自然段按原文顺序复原这一段的主要内容，"
        "再视需要加 3 到 8 条要点补充细节。"
        "章节正文必须保留原文里的关键名词、人名、设备名、时间、数字、例子、因果关系、比较和转折。"
        "如果原文在一个章节里连续讲了多个点，都要写进去，不要只留下一个总括句。"
        f"总共输出 3 到 {max_sections} 个章节，按视频逻辑顺序排列。\n\n"
        "章节标题要具体，不要写“转录片段”“片段总结”这种过程词。"
        "如果主题真的不明确，才使用“第 1 节”“第 2 节”。"
        "只基于输入内容，不要编造，不要广告，不要免责声明。\n\n"
        f"内容:\n{material}"
    )
