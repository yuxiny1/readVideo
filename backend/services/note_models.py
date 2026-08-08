from dataclasses import dataclass, field


@dataclass(frozen=True)
class ArticleSection:
    title: str
    body: str


@dataclass(frozen=True)
class ArticleNote:
    summary_items: list[str]
    sections: list[ArticleSection]
    summary_paragraphs: list[str] = field(default_factory=list)
    business_items: list[str] = field(default_factory=list)
    editorial_paragraphs: list[str] = field(default_factory=list)
