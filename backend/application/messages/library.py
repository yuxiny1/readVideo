from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ListHistoryQuery:
    pass


@dataclass(frozen=True)
class LookupHistoryQuery:
    url: str


@dataclass(frozen=True)
class GetHistoryQuery:
    task_id: str


@dataclass(frozen=True)
class UpdateHistoryTagsCommand:
    task_id: str
    tags: list[str]


@dataclass(frozen=True)
class GetHistoryFileQuery:
    task_id: str
    file_kind: str


@dataclass(frozen=True)
class ListFavoritesQuery:
    pass


@dataclass(frozen=True)
class ListFavoriteFoldersQuery:
    pass


@dataclass(frozen=True)
class CreateFavoriteFolderCommand:
    name: str
    notes: str


@dataclass(frozen=True)
class UpdateFavoriteFolderCommand:
    folder_id: int
    name: str
    notes: str


@dataclass(frozen=True)
class DeleteFavoriteFolderCommand:
    folder_id: int


@dataclass(frozen=True)
class CreateFavoriteCommand:
    task_id: str
    folder_id: Optional[int]


@dataclass(frozen=True)
class ReadFavoriteMarkdownQuery:
    item_id: int


@dataclass(frozen=True)
class AssignFavoriteFolderCommand:
    item_id: int
    folder_id: Optional[int]


@dataclass(frozen=True)
class UpdateFavoriteTagsCommand:
    item_id: int
    tags: list[str]


@dataclass(frozen=True)
class DeleteFavoriteCommand:
    item_id: int
