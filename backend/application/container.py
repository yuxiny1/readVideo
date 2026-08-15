from functools import lru_cache

from backend.application.handlers.library import (
    AssignFavoriteFolderHandler,
    CreateFavoriteFolderHandler,
    CreateFavoriteHandler,
    DeleteFavoriteFolderHandler,
    DeleteFavoriteHandler,
    GetHistoryFileHandler,
    GetHistoryHandler,
    ListFavoriteFoldersHandler,
    ListFavoritesHandler,
    ListHistoryHandler,
    LookupHistoryHandler,
    ReadFavoriteMarkdownHandler,
    UpdateFavoriteFolderHandler,
    UpdateFavoriteTagsHandler,
    UpdateHistoryTagsHandler,
)
from backend.application.handlers.models import (
    DownloadWhisperModelHandler,
    GetMlxStatusHandler,
    ListOllamaModelsHandler,
    ListTranscriptionModelsHandler,
    PullOllamaModelHandler,
)
from backend.application.handlers.reader import (
    ListMarkdownFilesHandler,
    ListTagsHandler,
    ReadMarkdownHandler,
    ResolveMarkdownDownloadHandler,
)
from backend.application.handlers.system import AppConfigHandler, HealthHandler, ReadinessHandler
from backend.application.handlers.tasks import (
    GetTaskHandler,
    ListTasksHandler,
    RunVideoProcessingHandler,
    StartVideoProcessingHandler,
    WorkerProbeHandler,
)
from backend.application.handlers.watchlist import (
    AddWatchItemHandler,
    DeleteWatchItemHandler,
    ListWatchItemUpdatesHandler,
    ListWatchlistHandler,
    ReorderWatchlistHandler,
    UpdateWatchItemHandler,
)
from backend.application.mediator import Mediator
from backend.application.messages.library import (
    AssignFavoriteFolderCommand,
    CreateFavoriteCommand,
    CreateFavoriteFolderCommand,
    DeleteFavoriteCommand,
    DeleteFavoriteFolderCommand,
    GetHistoryFileQuery,
    GetHistoryQuery,
    ListFavoriteFoldersQuery,
    ListFavoritesQuery,
    ListHistoryQuery,
    LookupHistoryQuery,
    ReadFavoriteMarkdownQuery,
    UpdateFavoriteFolderCommand,
    UpdateFavoriteTagsCommand,
    UpdateHistoryTagsCommand,
)
from backend.application.messages.models import (
    DownloadWhisperModelCommand,
    GetMlxStatusQuery,
    ListOllamaModelsQuery,
    ListTranscriptionModelsQuery,
    PullOllamaModelCommand,
)
from backend.application.messages.reader import (
    ListMarkdownFilesQuery,
    ListTagsQuery,
    ReadMarkdownQuery,
    ResolveMarkdownDownloadQuery,
)
from backend.application.messages.system import AppConfigQuery, HealthQuery, ReadinessQuery
from backend.application.messages.tasks import (
    GetTaskQuery,
    ListTasksQuery,
    RunVideoProcessingCommand,
    StartVideoProcessingCommand,
    WorkerProbeCommand,
)
from backend.application.messages.watchlist import (
    AddWatchItemCommand,
    DeleteWatchItemCommand,
    ListWatchItemUpdatesQuery,
    ListWatchlistQuery,
    ReorderWatchlistCommand,
    UpdateWatchItemCommand,
)


HANDLER_REGISTRATIONS = (
    (StartVideoProcessingCommand, StartVideoProcessingHandler),
    (RunVideoProcessingCommand, RunVideoProcessingHandler),
    (WorkerProbeCommand, WorkerProbeHandler),
    (GetTaskQuery, GetTaskHandler),
    (ListTasksQuery, ListTasksHandler),
    (ListHistoryQuery, ListHistoryHandler),
    (LookupHistoryQuery, LookupHistoryHandler),
    (GetHistoryQuery, GetHistoryHandler),
    (UpdateHistoryTagsCommand, UpdateHistoryTagsHandler),
    (GetHistoryFileQuery, GetHistoryFileHandler),
    (ListFavoritesQuery, ListFavoritesHandler),
    (ListFavoriteFoldersQuery, ListFavoriteFoldersHandler),
    (CreateFavoriteFolderCommand, CreateFavoriteFolderHandler),
    (UpdateFavoriteFolderCommand, UpdateFavoriteFolderHandler),
    (DeleteFavoriteFolderCommand, DeleteFavoriteFolderHandler),
    (CreateFavoriteCommand, CreateFavoriteHandler),
    (ReadFavoriteMarkdownQuery, ReadFavoriteMarkdownHandler),
    (AssignFavoriteFolderCommand, AssignFavoriteFolderHandler),
    (UpdateFavoriteTagsCommand, UpdateFavoriteTagsHandler),
    (DeleteFavoriteCommand, DeleteFavoriteHandler),
    (ListMarkdownFilesQuery, ListMarkdownFilesHandler),
    (ReadMarkdownQuery, ReadMarkdownHandler),
    (ResolveMarkdownDownloadQuery, ResolveMarkdownDownloadHandler),
    (ListTagsQuery, ListTagsHandler),
    (ListWatchlistQuery, ListWatchlistHandler),
    (AddWatchItemCommand, AddWatchItemHandler),
    (ReorderWatchlistCommand, ReorderWatchlistHandler),
    (DeleteWatchItemCommand, DeleteWatchItemHandler),
    (UpdateWatchItemCommand, UpdateWatchItemHandler),
    (ListWatchItemUpdatesQuery, ListWatchItemUpdatesHandler),
    (HealthQuery, HealthHandler),
    (ReadinessQuery, ReadinessHandler),
    (AppConfigQuery, AppConfigHandler),
    (ListOllamaModelsQuery, ListOllamaModelsHandler),
    (GetMlxStatusQuery, GetMlxStatusHandler),
    (PullOllamaModelCommand, PullOllamaModelHandler),
    (ListTranscriptionModelsQuery, ListTranscriptionModelsHandler),
    (DownloadWhisperModelCommand, DownloadWhisperModelHandler),
)


@lru_cache(maxsize=1)
def get_mediator() -> Mediator:
    mediator = Mediator()
    for request_type, handler_type in HANDLER_REGISTRATIONS:
        mediator.register(request_type, handler_type())
    return mediator
