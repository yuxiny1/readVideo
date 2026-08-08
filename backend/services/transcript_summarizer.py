"""Stable public facade for transcript-to-note behavior."""

from backend.services.extractive_summarizer import section_title, summarize_transcript
from backend.services.note_models import ArticleNote, ArticleSection
from backend.services.ollama_notes import build_article_note_with_ollama, summarize_transcript_with_ollama


def summarize_transcript_with_backend(
    transcript_text: str,
    backend: str = "extractive",
    ollama_model: str = "qwen3.6:35b",
    ollama_url: str = "http://127.0.0.1:11434/api/generate",
) -> list[str]:
    if backend == "extractive":
        return summarize_transcript(transcript_text)
    if backend == "ollama":
        return summarize_transcript_with_ollama(transcript_text, ollama_model, ollama_url)
    raise RuntimeError("总结引擎无效，请选择本地提取式总结或 Ollama 本地大模型。")


__all__ = [
    "ArticleNote",
    "ArticleSection",
    "build_article_note_with_ollama",
    "section_title",
    "summarize_transcript",
    "summarize_transcript_with_backend",
    "summarize_transcript_with_ollama",
]
