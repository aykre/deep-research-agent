"""DuckDuckGo search service."""

import logging
from typing import Literal

from ddgs import DDGS

from server.config import MAX_RESULTS_PER_QUERY

# Disable primp logger from ddgs library
logging.getLogger("primp").setLevel(logging.WARNING)


def duckduckgo_search(
    query: str,
    time_filter: Literal["d", "w", "m", "y"] | None = None,
    max_results: int = MAX_RESULTS_PER_QUERY,
) -> list[dict[str, str]]:
    """Search the web using DuckDuckGo.

    Args:
        query: Search query string
        time_filter: Optional time filter - d (day), w (week), m (month), y (year)
        max_results: Maximum number of results to return

    Returns:
        List of search results with title, url, snippet
    """
    with DDGS() as ddgs:
        results = list(
            ddgs.text(
                query,
                timelimit=time_filter,
                max_results=max_results,
                provider="duckduckgo",
            )
        )
    return [
        {"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")}
        for r in results
    ]
