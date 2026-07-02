from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from backend.application import get_mediator
from backend.application.messages.reader import (
    ListMarkdownFilesQuery,
    ListTagsQuery,
    ReadMarkdownQuery,
    ResolveMarkdownDownloadQuery,
)


router = APIRouter()


@router.get("/api/markdown_files")
async def get_markdown_files(directory: str = Query(default="")):
    return await get_mediator().send(ListMarkdownFilesQuery(directory))


@router.get("/api/markdown_files/download")
async def download_markdown_file(path: str):
    markdown_path = await get_mediator().send(ResolveMarkdownDownloadQuery(path))
    return FileResponse(markdown_path, filename=markdown_path.name, media_type="text/markdown")


@router.get("/api/markdown_files/read")
async def read_markdown_file(path: str):
    return await get_mediator().send(ReadMarkdownQuery(path))


@router.get("/api/tags")
async def list_tags():
    return await get_mediator().send(ListTagsQuery())
