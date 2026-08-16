from backend.services.language_model_notes import (
    build_article_note_with_client,
    summarize_transcript_with_client,
)
from backend.services.note_models import ArticleNote
from backend.services.ollama_client import OllamaClient


def summarize_transcript_with_ollama(
    transcript_text: str,
    model: str = "qwen3.6:35b",
    url: str = "http://127.0.0.1:11434/api/generate",
    timeout_seconds: int = 900,
    max_items: int = 8,
    chunk_chars: int = 7000,
) -> list[str]:
    return summarize_transcript_with_client(
        transcript_text,
        OllamaClient(model, url, timeout_seconds),
        "Ollama",
        max_items=max_items,
        chunk_chars=chunk_chars,
    )


def build_article_note_with_ollama(
    transcript_text: str,
    model: str = "qwen3.6:35b",
    url: str = "http://127.0.0.1:11434/api/generate",
    timeout_seconds: int = 900,
    max_summary_items: int = 7,
    max_sections: int = 10,
    chunk_chars: int = 5200,
    note_style: str = "detailed",
) -> ArticleNote:
    return build_article_note_with_client(
        transcript_text,
        OllamaClient(model, url, timeout_seconds),
        "Ollama",
        max_summary_items=max_summary_items,
        max_sections=max_sections,
        chunk_chars=chunk_chars,
        note_style=note_style,
    )
