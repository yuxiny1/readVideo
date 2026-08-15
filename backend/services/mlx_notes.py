from backend.services.language_model_notes import (
    build_article_note_with_client,
    summarize_transcript_with_client,
)
from backend.services.mlx_client import MlxClient
from backend.services.note_models import ArticleNote


def summarize_transcript_with_mlx(
    transcript_text: str,
    model: str = "mlx-community/Qwen2.5-72B-Instruct-3bit",
    url: str = "http://127.0.0.1:8080/v1/chat/completions",
    timeout_seconds: int = 900,
    max_items: int = 8,
    chunk_chars: int = 7000,
) -> list[str]:
    return summarize_transcript_with_client(
        transcript_text,
        MlxClient(model, url, timeout_seconds),
        "MLX 本地模型",
        max_items=max_items,
        chunk_chars=chunk_chars,
    )


def build_article_note_with_mlx(
    transcript_text: str,
    model: str = "mlx-community/Qwen2.5-72B-Instruct-3bit",
    url: str = "http://127.0.0.1:8080/v1/chat/completions",
    timeout_seconds: int = 900,
    max_summary_items: int = 7,
    max_sections: int = 10,
    chunk_chars: int = 5200,
    note_style: str = "detailed",
) -> ArticleNote:
    return build_article_note_with_client(
        transcript_text,
        MlxClient(model, url, timeout_seconds),
        "MLX 本地模型",
        max_summary_items=max_summary_items,
        max_sections=max_sections,
        chunk_chars=chunk_chars,
        note_style=note_style,
    )
