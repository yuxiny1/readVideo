from backend.core.config import load_settings
from backend.storage.favorites import FavoriteStore
from backend.storage.history import HistoryStore
from backend.storage.tags import TagStore
from backend.storage.watchlist import WatchlistStore


def history_store() -> HistoryStore:
    return HistoryStore(load_settings().database_path)


def favorite_store() -> FavoriteStore:
    return FavoriteStore(load_settings().database_path)


def tag_store() -> TagStore:
    return TagStore(load_settings().database_path)


def watchlist_store() -> WatchlistStore:
    return WatchlistStore(load_settings().database_path)


def history_record_dict(record, tags: list[str]) -> dict:
    return {**record.__dict__, "tags": tags}


def favorite_dict(item, tags: list[str]) -> dict:
    return {**item.__dict__, "tags": tags}
