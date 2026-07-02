from dataclasses import dataclass


@dataclass(frozen=True)
class ListMarkdownFilesQuery:
    directory: str = ""


@dataclass(frozen=True)
class ReadMarkdownQuery:
    path: str


@dataclass(frozen=True)
class ResolveMarkdownDownloadQuery:
    path: str


@dataclass(frozen=True)
class ListTagsQuery:
    pass
