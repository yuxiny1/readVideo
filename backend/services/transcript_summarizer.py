"""Stable public facade for transcript-to-note behavior."""

from backend.services.extractive_summarizer import section_title, summarize_transcript
from backend.services.note_models import ArticleNote, ArticleSection
from backend.services.mlx_notes import build_article_note_with_mlx, summarize_transcript_with_mlx
from backend.services.ollama_notes import build_article_note_with_ollama, summarize_transcript_with_ollama


def summarize_transcript_with_backend(
    transcript_text: str,
    backend: str = "extractive",
    ollama_model: str = "qwen3.6:35b",
    ollama_url: str = "http://127.0.0.1:11434/api/generate",
    mlx_model: str = "mlx-community/Qwen2.5-72B-Instruct-3bit",
    mlx_url: str = "http://127.0.0.1:8080/v1/chat/completions",
) -> list[str]:
    if backend == "extractive":
        return summarize_transcript(transcript_text)
    if backend == "ollama":
        return summarize_transcript_with_ollama(transcript_text, ollama_model, ollama_url)
    if backend == "mlx":
        return summarize_transcript_with_mlx(transcript_text, mlx_model, mlx_url)
    raise RuntimeError("总结引擎无效，请选择本地提取式总结、Ollama 或 MLX 本地大模型。")


__all__ = [
    "ArticleNote",
    "ArticleSection",
    "build_article_note_with_ollama",
    "build_article_note_with_mlx",
    "section_title",
    "summarize_transcript",
    "summarize_transcript_with_backend",
    "summarize_transcript_with_ollama",
    "summarize_transcript_with_mlx",
]
