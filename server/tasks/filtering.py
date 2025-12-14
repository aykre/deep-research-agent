"""Search result filtering task using LLM."""

from langgraph.func import task

from server.utils.util import (
    call_llm_with_cancel,
    create_task_llm,
    create_llm_messages,
    parse_json_response,
)
from server.config import MAX_RESULTS_FILTERED, FILTER_LLM_MODEL, FILTER_REASONING_EFFORT
from server.models import FilteredSearchResult, SearchResult, TitleFilterOutput
from server.prompts import load_prompt
from server.utils.url_filters import is_ad_or_tracking_url
from server.utils.logging_config import get_logger

logger = get_logger(__name__)


@task
async def filter_search_results_by_titles(
    query: str,
    search_results: list[SearchResult],
    stop_flag: dict[str, bool],
) -> tuple[TitleFilterOutput, bool]:
    """Filter search results by relevance using LLM.

    Args:
        query: The search query
        search_results: List of search results to filter
        stop_flag: Dictionary to signal task cancellation

    Returns:
        Tuple of (TitleFilterOutput, cancelled) where TitleFilterOutput contains filtered results
    """
    # Pre-filter: Remove ad/tracking URLs
    clean_results = []
    rejected_count = 0

    for result in search_results:
        if is_ad_or_tracking_url(result.url):
            logger.info("Filtered out ad/tracking URL", url=result.url)
            rejected_count += 1
        else:
            clean_results.append(result)

    if not clean_results:
        logger.warning(
            "All search results were filtered out as ads/tracking URLs",
            total_results=len(search_results),
        )
        return TitleFilterOutput(
            query=query,
            total_results=len(search_results),
            relevant_results=[],
            filtered_out=len(search_results),
            avg_relevance_score=0.0,
        ), False

    # Continue with LLM-based filtering on clean results
    llm = create_task_llm(FILTER_LLM_MODEL, FILTER_REASONING_EFFORT)

    system_prompt = load_prompt("filter_system")

    # Prepare search results for analysis
    results_text = "\n".join(
        [
            f"{i + 1}. Title: {r.title}\n   URL: {r.url}\n   Snippet: {r.snippet}\n"
            for i, r in enumerate(clean_results)
        ]
    )

    task_prompt = load_prompt("filter_task").format(
        query=query,
        results_text=results_text,
    )

    messages = create_llm_messages(system_prompt, task_prompt)

    content, cancelled = await call_llm_with_cancel(stop_flag, llm, messages)
    if cancelled:
        return TitleFilterOutput(
            query=query,
            total_results=len(search_results),
            relevant_results=[],
            filtered_out=len(search_results),
            avg_relevance_score=0.0,
        ), True

    try:
        result = parse_json_response(content)

        filtered_results = []
        for item in result.get("filtered_results", []):
            filtered_results.append(
                FilteredSearchResult(
                    title=item["title"],
                    url=item["url"],
                    snippet=item["snippet"],
                    relevance_score=float(item["relevance_score"]),
                )
            )

        total_results = len(search_results)
        relevant_count = len(filtered_results)
        filtered_out = total_results - relevant_count
        avg_score = (
            sum(r.relevance_score for r in filtered_results) / relevant_count
            if relevant_count > 0
            else 0.0
        )
        # Take only top k
        filtered_results = sorted(
            filtered_results, key=lambda v: v.relevance_score, reverse=True
        )[:MAX_RESULTS_FILTERED]

        return TitleFilterOutput(
            query=query,
            total_results=total_results,
            relevant_results=filtered_results,
            filtered_out=filtered_out,
            avg_relevance_score=avg_score,
        ), False

    except Exception:
        # Fallback: return all clean results with neutral scores
        fallback_results = [
            FilteredSearchResult(
                title=r.title,
                url=r.url,
                snippet=r.snippet,
                relevance_score=0.7,  # Default moderate relevance
            )
            for r in clean_results
        ][:MAX_RESULTS_FILTERED]

        return TitleFilterOutput(
            query=query,
            total_results=len(search_results),
            relevant_results=fallback_results,
            filtered_out=rejected_count,
            avg_relevance_score=0.7,
        ), False
