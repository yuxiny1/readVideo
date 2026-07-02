from dataclasses import dataclass


@dataclass(frozen=True)
class ListWatchlistQuery:
    pass


@dataclass(frozen=True)
class AddWatchItemCommand:
    name: str
    url: str
    notes: str


@dataclass(frozen=True)
class ReorderWatchlistCommand:
    item_ids: list[int]


@dataclass(frozen=True)
class DeleteWatchItemCommand:
    item_id: int


@dataclass(frozen=True)
class UpdateWatchItemCommand:
    item_id: int
    name: str
    url: str
    notes: str


@dataclass(frozen=True)
class ListWatchItemUpdatesQuery:
    item_id: int
    limit: int
