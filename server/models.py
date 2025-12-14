from datetime import datetime
from typing import Literal, Union
from pydantic import BaseModel


# Type alias for time filters
TimeFilter = Literal["d", "w", "m", "y"] | None


# Query with optional time filter (for rewriter output)
class QueryWithFilter(BaseModel):
    query: str
    time_filter: TimeFilter = None
    strategy: str | None = None  # Track which strategy generated this query


# Structured output from the rewriter agent
class RewriterOutput(BaseModel):
    action: Literal["continue", "stop", "cancelled"]
    requires_recency: bool = False  # LLM decides if topic needs recent info
    queries: list[QueryWithFilter] = []


# Search result from DuckDuckGo
class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


# Filtered search result with relevance score
class FilteredSearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    relevance_score: float  # 0.0 to 1.0


# Output from title filtering task
class TitleFilterOutput(BaseModel):
    query: str
    total_results: int
    relevant_results: list[FilteredSearchResult]
    filtered_out: int
    avg_relevance_score: float


# Base page content - all types include these fields
class PageContent(BaseModel):
    page_type: str
    title: str
    url: str


class ArticleContent(PageContent):
    page_type: Literal["article"] = "article"
    content: str
    author: str | None = None
    date: str | None = None


class ProductContent(PageContent):
    page_type: Literal["product"] = "product"
    name: str | None = None
    price: str | None = None
    options: list[str] = []
    description: str | None = None
    features: list[str] = []


class ForumPostContent(PageContent):
    page_type: Literal["forum_post"] = "forum_post"
    content: str
    author: str | None = None
    replies: list[str] = []


class DirectoryItem(BaseModel):
    title: str
    url: str | None = None
    description: str | None = None
    price: str | None = None


class DirectoryContent(PageContent):
    page_type: Literal["directory"] = "directory"
    items: list[DirectoryItem] = []


class OtherContent(PageContent):
    page_type: Literal["other"] = "other"
    content: str


# Union type for all page content types
ExtractedContent = Union[
    ArticleContent,
    ProductContent,
    ForumPostContent,
    DirectoryContent,
    OtherContent,
]


# WebSocket message types
class ResearchRequest(BaseModel):
    query: str


class ResearchEvent(BaseModel):
    type: str
    data: dict
    timestamp: datetime = datetime.now()


# WebSocket client message types
class StartMessage(BaseModel):
    action: Literal["start"]
    query: str


class StopMessage(BaseModel):
    action: Literal["stop"]


ClientMessage = Union[StartMessage, StopMessage]
