from dataclasses import dataclass


@dataclass(frozen=True)
class ListOllamaModelsQuery:
    pass


@dataclass(frozen=True)
class PullOllamaModelCommand:
    model: str


@dataclass(frozen=True)
class ListTranscriptionModelsQuery:
    pass


@dataclass(frozen=True)
class DownloadWhisperModelCommand:
    model: str
