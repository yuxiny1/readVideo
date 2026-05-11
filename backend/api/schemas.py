from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class ProcessVideoRequest(BaseModel):
    url: HttpUrl
    task_id: Optional[str] = Field(default=None, min_length=1)
    notes_dir: Optional[str] = Field(default=None, min_length=1)
    notes_backend: Optional[str] = Field(default=None, min_length=1)
    ollama_model: Optional[str] = Field(default=None, min_length=1)


class WatchItemRequest(BaseModel):
    name: str = Field(min_length=1)
    url: HttpUrl
    notes: str = ""


class WatchItemUpdateRequest(BaseModel):
    name: str = Field(min_length=1)
    url: HttpUrl
    notes: str = ""


class WatchlistReorderRequest(BaseModel):
    item_ids: list[int] = Field(min_length=1)


class OllamaPullRequest(BaseModel):
    model: str = Field(min_length=1)


class FavoriteRequest(BaseModel):
    task_id: str = Field(min_length=1)
    folder_id: Optional[int] = None


class FavoriteFolderRequest(BaseModel):
    name: str = Field(min_length=1)
    notes: str = ""


class FavoriteFolderAssignmentRequest(BaseModel):
    folder_id: Optional[int] = None
