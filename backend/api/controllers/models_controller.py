from fastapi import APIRouter

from backend.api.schemas import OllamaPullRequest, WhisperModelDownloadRequest
from backend.application import get_mediator
from backend.application.messages.models import (
    DownloadWhisperModelCommand,
    ListOllamaModelsQuery,
    ListTranscriptionModelsQuery,
    PullOllamaModelCommand,
)


router = APIRouter()


@router.get("/api/ollama/models")
async def get_ollama_models():
    return await get_mediator().send(ListOllamaModelsQuery())


@router.post("/api/ollama/pull")
async def pull_ollama_model(request: OllamaPullRequest):
    return await get_mediator().send(PullOllamaModelCommand(request.model))


@router.get("/api/transcription/models")
async def get_transcription_models():
    return await get_mediator().send(ListTranscriptionModelsQuery())


@router.post("/api/transcription/models/download")
async def download_transcription_model(request: WhisperModelDownloadRequest):
    return await get_mediator().send(DownloadWhisperModelCommand(request.model))
