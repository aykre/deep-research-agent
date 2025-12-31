"""Main research workflow orchestration using LangGraph.

This module implements a multi-agent research system that:
1. Searches the web using DuckDuckGo
2. Scrapes pages with Playwright or bs4
3. Extracts structured content using LLM
4. Rewrites queries for deeper research
5. Synthesizes findings into a coherent response
"""

from dataclasses import dataclass, field
from typing import Any
import asyncio
from uuid import uuid4

from langgraph.config import get_stream_writer
from langgraph.func import entrypoint

from server.config import (
    MAX_REWRITTEN_QUERIES,
    MAX_RESULTS_PER_QUERY,
    USE_PLAYWRIGHT,
    USE_GUARDRAILS,
    USE_EXTRACTION,
)
from server.models import ExtractedContent, SearchResult
from server.services.browser_pool import get_browser_pool
from server.services.search import duckduckgo_search
from server.tasks.extraction import create_extracted_content, scrape_and_extract_task
from server.tasks.filtering import filter_search_results_by_titles
from server.tasks.guardrail import check_query_safety
from server.tasks.rewriter import _build_content_summary, rewrite_queries_task
from server.tasks.writer import write_response_task
from server.utils.content_validators import has_meaningful_content
from server.utils.logging_config import bind_request_context, get_logger

logger = get_logger(__name__)


@dataclass
class ResearchState:
    """Holds all state for a research session."""

    original_query: str
    request_id: str
    connection_id: str
    seen_urls: list[str] = field(default_factory=list)
    searches: list[dict] = field(default=dict)
    extracted_content: list[ExtractedContent] = field(default_factory=list)
    queries_executed: list[str] = field(default_factory=list)
    total_rewritten_queries: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)


def _emit_event(event_type: str, data: dict, check_stop=None) -> None:
    """Emit an event to the client, optionally checking stop flag first.

    This function sends an event to the client through the stream writer, with an
    optional check to see if the research has been stopped.

    Args:
        event_type: The type of event to emit (e.g., "progress", "search_and_filter_started")
        data: Event data dictionary containing relevant information for the event
        check_stop: Optional callable that returns True if research is stopped
    """
    if check_stop and check_stop():
        return

    writer = get_stream_writer()
    writer({"type": event_type, "data": data})


def _emit_progress(current_step: int, total_steps: int, check_stop=None) -> None:
    """Emit a progress event.

    This function emits a progress update event to the client, showing the current
    step and total number of steps in the research process.

    Args:
        current_step: The current step number in the research process
        total_steps: The total number of steps in the research process
        check_stop: Optional callable that returns True if research is stopped
    """
    _emit_event(
        "progress",
        {"current_step": current_step, "total_steps": total_steps},
        check_stop,
    )


def _deduplicate_search_results(
    search_results: list[dict[str, str]],
    seen_urls_set: set[str],
    max_results: int,
) -> tuple[list[SearchResult], list[str]]:
    """Deduplicate search results and return new URLs found.

    This function filters out duplicate URLs from search results and limits the
    number of results to the specified maximum. It returns both the deduplicated
    results and the new URLs that were found.

    Args:
        search_results: List of search result dictionaries from the search engine
        seen_urls_set: Set of URLs that have already been processed
        max_results: Maximum number of results to return

    Returns:
        Tuple of (new_results, new_urls_found) where:
        - new_results: List of SearchResult objects that are new and within the limit
        - new_urls_found: List of URLs that were newly discovered
    """
    new_results: list[SearchResult] = []
    new_urls: list[str] = []

    for r in search_results:
        if r["url"] not in seen_urls_set and len(new_results) < max_results:
            new_results.append(SearchResult(**r))
            new_urls.append(r["url"])
            seen_urls_set.add(
                r["url"]
            )  # Add to local snapshot to avoid duplicates within this batch

    return new_results, new_urls


async def _search_and_filter(
    query: str,
    max_results: int,
    seen_urls_set: set[str],
    time_filter: Any,
    stage_id: str,
    check_stop,
    stop_flag: dict[str, bool],
) -> tuple[list[SearchResult], list[str]]:
    try:
        logger.info("Starting search", query=query, time_filter=time_filter)
        _emit_event(
            "search_and_filter_started",
            {"stage_id": stage_id, "query": query, "time_filter": time_filter},
        )

        search_results = duckduckgo_search(
            query, time_filter=time_filter, max_results=max_results
        )
        logger.info(
            "Search completed",
            query=query,
            result_count=len(search_results),
            time_filter=time_filter,
        )

        # Deduplicate and limit results
        new_results, new_urls = _deduplicate_search_results(
            search_results, seen_urls_set, max_results
        )

        # Filter search results by title relevance
        if new_results:
            logger.info(
                "Filtering new results", query=query, result_count=len(new_results)
            )
            filter_output, cancelled = await filter_search_results_by_titles(
                query, new_results, stop_flag
            )

            # Convert filtered results back to SearchResult for compatibility
            filtered_results = [
                SearchResult(title=fr.title, url=fr.url, snippet=fr.snippet)
                for fr in filter_output.relevant_results
            ]

            logger.info(
                "Filter complete",
                query=query,
                relevant_results=len(filter_output.relevant_results),
                filtered_out=filter_output.filtered_out,
                avg_score=round(filter_output.avg_relevance_score, 2),
            )
            _emit_event(
                "search_and_filter_completed",
                {
                    "stage_id": stage_id,
                    "query": query,
                    "total_results": filter_output.total_results,
                    "relevant_count": len(filter_output.relevant_results),
                    "filtered_out": filter_output.filtered_out,
                    "avg_relevance_score": filter_output.avg_relevance_score,
                    "results": [
                        fr.model_dump() for fr in filter_output.relevant_results
                    ],
                },
                check_stop,
            )

            # Only return URLs for results that passed filtering
            filtered_urls = [r.url for r in filtered_results]
            return filtered_results, filtered_urls
        else:
            _emit_event(
                "search_and_filter_completed",
                {
                    "stage_id": stage_id,
                    "query": query,
                    "total_results": 0,
                    "relevant_count": 0,
                    "filtered_out": 0,
                    "results": [],
                },
                check_stop,
            )
            return [], []
    except Exception as e:
        logger.error(
            "Search and filter failed", query=query, error=str(e), exc_info=True
        )
        _emit_event(
            "search_and_filter_failed",
            {"stage_id": stage_id, "query": query, "error": str(e)},
            check_stop,
        )
        raise


async def _scrape_and_extract_results(
    results: list[SearchResult],
    state: ResearchState,
    check_stop,
    stop_flag: dict[str, bool],
) -> None:
    """Scrape and extract content from multiple URLs in parallel.

    This function processes a list of search results by scraping their URLs and
    extracting structured content from the pages. It handles parallel execution,
    error handling, and updates the research state with the extracted content.

    Args:
        results: List of SearchResult objects to scrape and extract
        state: ResearchState object to update with extracted content
    check_stop: Callable that returns True if research should be stopped
    stop_flag: Dictionary containing stop flag for cancellation
    """
    try:
        logger.info(
            "Starting scrape and extract batch",
            url_count=len(results),
            use_extraction=USE_EXTRACTION,
        )
        # Emit scrape_started for all results upfront
        for result in results:
            stage_id = f"scrape_{result.url}"
            _emit_event(
                "scrape_started",
                {"stage_id": stage_id, "url": result.url, "title": result.title},
            )

        # If extraction is disabled, just scrape without extraction
        if not USE_EXTRACTION:
            from server.services.scraper import scrape_page
            from server.models import OtherContent

            logger.info("Extraction disabled, scraping pages without LLM extraction")

            async def scrape_job(result: SearchResult) -> dict:
                """Scrape a single URL and return result dict."""
                scrape_stage_id = f"scrape_{result.url}"
                try:
                    content = await scrape_page(
                        result.url, use_playwright=USE_PLAYWRIGHT
                    )
                    if content:
                        # Create basic OtherContent with scraped content
                        extracted = OtherContent(
                            title=result.title,
                            url=result.url,
                            content=content,  # Truncate like extraction does
                        )
                        return {
                            "success": True,
                            "url": result.url,
                            "title": result.title,
                            "stage_id": scrape_stage_id,
                            "extracted": extracted,
                        }
                    else:
                        return {
                            "success": False,
                            "url": result.url,
                            "title": result.title,
                            "stage_id": scrape_stage_id,
                            "error": "No content scraped",
                        }
                except Exception as e:
                    return {
                        "success": False,
                        "url": result.url,
                        "title": result.title,
                        "stage_id": scrape_stage_id,
                        "error": str(e),
                    }

            # Launch all scrape tasks in parallel
            scrape_jobs = [
                asyncio.create_task(scrape_job(result)) for result in results
            ]

            # Process results as they complete
            for task_future in asyncio.as_completed(scrape_jobs):
                task_result = await task_future

                if task_result["success"]:
                    state.extracted_content.append(task_result["extracted"])
                    logger.info("Successfully scraped page", url=task_result["url"])
                    _emit_event(
                        "scrape_complete",
                        {
                            "stage_id": task_result["stage_id"],
                            "url": task_result["url"],
                            "success": True,
                        },
                        check_stop,
                    )
                else:
                    logger.warning("Failed to scrape page", url=task_result["url"])
                    _emit_event(
                        "scrape_complete",
                        {
                            "stage_id": task_result["stage_id"],
                            "url": task_result["url"],
                            "success": False,
                            "error": task_result.get("error"),
                        },
                        check_stop,
                    )
            return

        # Launch all scrape/extract tasks in parallel
        scrape_jobs = []
        for result in results:
            task = scrape_and_extract_task(
                result.url,
                result.title,
                stop_flag,
            )
            scrape_jobs.append(task)

        # Process results as they complete
        for task_future in asyncio.as_completed(scrape_jobs):
            task_result, cancelled = await task_future

            extraction_stage_id = f"extract_{task_result['url']}"

            if cancelled:
                _emit_event(
                    "extraction_complete",
                    {
                        "stage_id": extraction_stage_id,
                        "url": task_result["url"],
                        "page_type": "unknown",
                        "title": "Extraction failed",
                        "error": "Research stopped",
                    },
                )
                continue
            # Log errors to console
            if not task_result["success"] and task_result.get("error"):
                logger.error(
                    "Failed to scrape",
                    url=task_result["url"],
                    error=task_result.get("error"),
                )

            # Only emit extraction_complete if scrape was successful
            if task_result["success"]:
                if task_result["extracted"]:
                    # Reconstruct the ExtractedContent from the dict
                    extracted_dict = task_result["extracted"]
                    page_type = extracted_dict["page_type"]
                    extracted = create_extracted_content(page_type, extracted_dict)

                    # Validate content quality before adding to state
                    if has_meaningful_content(extracted):
                        state.extracted_content.append(extracted)
                        logger.info(
                            "Successfully extracted content",
                            url=task_result["url"],
                            page_type=extracted.page_type,
                        )
                        _emit_event(
                            "extraction_complete",
                            {
                                "stage_id": extraction_stage_id,
                                "url": task_result["url"],
                                "page_type": extracted.page_type,
                                "title": extracted.title,
                            },
                            check_stop,
                        )
                    else:
                        # Content quality check failed
                        logger.info(
                            "Filtered out low-quality content", url=task_result["url"]
                        )
                        _emit_event(
                            "extraction_complete",
                            {
                                "stage_id": extraction_stage_id,
                                "url": task_result["url"],
                                "page_type": "low_quality",
                                "title": "Content filtered (low quality)",
                            },
                            check_stop,
                        )
                else:
                    # Extraction returned no content or failed
                    extraction_error = task_result.get(
                        "extraction_error", "No content extracted"
                    )
                    logger.warning(
                        "Extraction failed for URL",
                        url=task_result["url"],
                        error=extraction_error,
                    )
                    _emit_event(
                        "extraction_complete",
                        {
                            "stage_id": extraction_stage_id,
                            "url": task_result["url"],
                            "page_type": "unknown",
                            "title": "Extraction failed",
                            "error": extraction_error,
                        },
                        check_stop,
                    )
    except Exception as e:
        logger.error("Scrape and extract batch failed", error=str(e), exc_info=True)
        raise


async def _process_rewritten_query(
    query_with_filter: Any,
    state: ResearchState,
    max_results: int,
    query_index: int,
    check_stop,
    stop_flag: dict[str, bool],
) -> dict:
    """Process a single rewritten query and return results.

    Note: Does NOT scrape results - that happens after state update to avoid race conditions.

    Returns:
        Dict with keys: query, filtered_results, new_urls, success
    """
    new_query = query_with_filter.query
    time_filter = query_with_filter.time_filter

    # Create a set snapshot for fast O(1) lookups (doesn't mutate state)
    seen_urls_set = set(state.seen_urls)

    stage_id = f"search_filter_{query_index}"
    filtered_results, new_urls = await _search_and_filter(
        new_query,
        max_results,
        seen_urls_set,
        time_filter,
        stage_id,
        check_stop,
        stop_flag,
    )

    if check_stop():
        return {
            "query": new_query,
            "filtered_results": [],
            "new_urls": [],
            "success": False,
        }

    return {
        "query": new_query,
        "filtered_results": filtered_results,
        "new_urls": new_urls,
        "success": True,
    }


async def _update_state_from_batch(
    state: ResearchState,
    batch_results: list[dict],
    max_queries: int,
    emit_progress: bool = True,
) -> None:
    """Safely update state with results from parallel batch execution.

    This function updates the research state with results from a batch of parallel
    query executions. It handles thread safety using a lock and can optionally
    emit progress events.

    Args:
        state: ResearchState object to update
        batch_results: List of results from batch execution
        max_queries: Maximum number of queries allowed
        emit_progress: If False, caller will emit progress after scraping completes
    """
    async with state._lock:
        for result in batch_results:
            if result["success"]:
                state.queries_executed.append(result["query"])
                state.total_rewritten_queries += 1
                state.searches.extend(result["filtered_results"])
                # Add new URLs to seen_urls under lock
                for url in result["new_urls"]:
                    if url not in state.seen_urls:  # Double-check for safety
                        state.seen_urls.append(url)

                # Emit progress event (if requested)
                if emit_progress:
                    _emit_progress(state.total_rewritten_queries + 1, max_queries + 2)


async def _iterative_query_rewriting(
    state: ResearchState,
    max_queries: int,
    max_results: int,
    check_stop,
    stop_flag: dict[str, bool],
) -> bool:
    """Iteratively rewrite queries to gather comprehensive research content.

    This function performs iterative query rewriting to gather comprehensive
    research content. It generates new queries based on existing findings,
    executes them, and continues the process until the maximum number of
    queries is reached or sufficient coverage is achieved.

    Args:
        state: ResearchState object containing current research state
        max_queries: Maximum number of queries to execute
        max_results: Maximum results per query
        check_stop: Callable that returns True if research should be stopped
        stop_flag: Dictionary containing stop flag for cancellation

    Returns:
        bool: True if recency filtering is required for the final response
    """
    requires_recency = False

    logger.info("Starting iterative query rewriting", max_queries=max_queries)
    while state.total_rewritten_queries < max_queries:
        if check_stop():
            break

        logger.info(
            "Rewrite iteration",
            iteration=state.total_rewritten_queries + 1,
            max_queries=max_queries,
            queries_executed=len(state.queries_executed),
            content_sources=len(state.extracted_content),
        )
        content_summary = _build_content_summary(state.searches)
        rewrite_stage_id = f"rewriter_{len(state.queries_executed)}"

        # Emit rewriter_started event
        _emit_event(
            "rewriter_started",
            {
                "stage_id": rewrite_stage_id,
                "queries_executed_count": len(state.queries_executed),
            },
        )
        # Get new queries from rewriter
        rewriter_output, cancelled = await rewrite_queries_task(
            state.original_query,
            state.queries_executed,
            content_summary,
            stop_flag=stop_flag,
        )

        if check_stop():
            _emit_event("stopped", {"has_data": len(state.extracted_content) > 0})
            break

        if rewriter_output.action == "stop":
            logger.info("Rewriter decided to stop", reason="sufficient_coverage")
            _emit_event(
                "rewriter_complete",
                {
                    "stage_id": rewrite_stage_id,
                    "action": "stop",
                    "queries_count": len(rewriter_output.queries),
                    "queries": [
                        {"query": q.query, "strategy": q.strategy}
                        for q in rewriter_output.queries
                    ],
                },
            )
            break

        logger.info(
            "Rewriter generated new queries",
            query_count=len(rewriter_output.queries),
            queries=[q.query for q in rewriter_output.queries],
        )
        _emit_event(
            "rewriter_complete",
            {
                "stage_id": rewrite_stage_id,
                "action": "continue",
                "queries_count": len(rewriter_output.queries),
                "queries": [
                    {"query": q.query, "strategy": q.strategy}
                    for q in rewriter_output.queries
                ],
            },
        )

        if rewriter_output.requires_recency:
            requires_recency = True

        # Determine how many queries we can process in this batch
        remaining_budget = max_queries - state.total_rewritten_queries
        queries_to_process = rewriter_output.queries[:remaining_budget]

        if not queries_to_process:
            break

        # Process queries in parallel using asyncio.gather
        tasks = []
        task_metadata: list[tuple[str, str]] = []
        for idx, query_with_filter in enumerate(queries_to_process):
            query_index = state.total_rewritten_queries + idx
            stage_id = f"search_filter_{query_index}"
            task = _process_rewritten_query(
                query_with_filter,
                state,
                max_results,
                query_index,
                check_stop,
                stop_flag,
            )
            tasks.append(task)
            task_metadata.append((stage_id, query_with_filter.query))

        # Wait for all queries in this batch to complete
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        successful_results = []
        for i, result in enumerate(batch_results):
            if isinstance(result, Exception):
                logger.error(
                    "Query execution failed",
                    index=i,
                    error=str(result),
                    exc_info=result,
                )
                stage_id, failed_query = task_metadata[i]
                _emit_event(
                    "search_and_filter_failed",
                    {"stage_id": stage_id, "query": failed_query, "error": str(result)},
                    check_stop,
                )
            elif isinstance(result, dict) and result.get("success"):
                successful_results.append(result)

        # Update state with batch results (adds URLs under lock)
        # Don't emit progress yet - wait until after scraping completes
        await _update_state_from_batch(
            state, successful_results, max_queries, emit_progress=False
        )

        # Collect all results to scrape, deduplicating by URL
        urls_to_scrape_set: set[str] = set()
        results_to_scrape: list[SearchResult] = []

        for result in successful_results:
            if result.get("filtered_results"):
                for search_result in result["filtered_results"]:
                    if search_result.url not in urls_to_scrape_set:
                        urls_to_scrape_set.add(search_result.url)
                        results_to_scrape.append(search_result)

        # Now scrape all results in one batch (already deduplicated)
        if results_to_scrape and not check_stop():
            logger.info(
                "Scraping deduplicated URLs from batch",
                url_count=len(results_to_scrape),
            )
            await _scrape_and_extract_results(
                results_to_scrape, state, check_stop, stop_flag
            )
        else:
            logger.info("No new results to scrape in this batch")

        # Emit progress event now that scraping is complete
        # Note: state.total_rewritten_queries was already updated in _update_state_from_batch
        _emit_progress(state.total_rewritten_queries + 1, max_queries + 2)

        # Stop if we hit the budget
        if state.total_rewritten_queries >= max_queries or check_stop():
            break

    return requires_recency


async def _generate_final_response(
    state: ResearchState,
    requires_recency: bool,
) -> str:
    """Generate the final research response from extracted content.

    This function synthesizes the gathered research content into a coherent
    final response, taking into account whether recency filtering is required.

    Args:
        state: ResearchState object containing extracted content
        requires_recency: Whether to prioritize recent content in the response

    Returns:
        str: The generated final research response
    """
    stage_id = "writing_response"
    try:
        if state.extracted_content:
            logger.info(
                "Generating final response",
                source_count=len(state.extracted_content),
                requires_recency=requires_recency,
            )
            _emit_event(
                "writing_started",
                {"stage_id": stage_id, "requires_recency": requires_recency},
            )

            content_dicts = [c.model_dump() for c in state.extracted_content]

            final_response = await write_response_task(
                state.original_query,
                content_dicts,
                requires_recency,
            )

            logger.info("Response", content=final_response)

            logger.info("Final response generated successfully")
            _emit_event("writing_complete", {"stage_id": stage_id})
            return final_response
        else:
            logger.warning("No content was gathered during research")
            return "No content was gathered."
    except Exception as e:
        logger.error("Failed to generate final response", error=str(e), exc_info=True)
        raise


@entrypoint()
async def research_workflow(inputs: dict[str, Any]) -> dict[str, Any]:
    """Execute the main research workflow.

    This is the main entry point for the research system. It orchestrates the entire
    research process including initial search, iterative query rewriting, content
    extraction, and final response generation.

    Args:
        inputs: Dictionary containing:
            - query: The original research query
            - stop_flag: Optional dictionary containing stop flag for cancellation

    Returns:
        dict: Dictionary containing:
            - status: "complete", "stopped", or "rejected"
            - response: The generated research response
            - sources: List of extracted content sources
            - rejection_reason: Optional reason if query was rejected
    """
    query = inputs["query"]
    request_id = inputs.get("request_id") or str(uuid4())
    connection_id = inputs.get("connection_id") or "unknown_connection"
    max_queries = MAX_REWRITTEN_QUERIES
    max_results = MAX_RESULTS_PER_QUERY
    stop_flag: dict[str, bool] = inputs.get("stop_flag", {"stopped": False})

    bind_request_context(request_id=request_id, connection_id=connection_id)

    logger.info("Starting research workflow", query=query)
    logger.info(
        "Workflow configuration",
        max_queries=max_queries,
        max_results=max_results,
        use_playwright=USE_PLAYWRIGHT,
    )

    state = ResearchState(
        original_query=query, request_id=request_id, connection_id=connection_id
    )

    def check_stop() -> bool:
        return stop_flag.get("stopped", False)

    browser_pool = get_browser_pool() if USE_PLAYWRIGHT else None

    try:
        # Start browser pool if needed (reference counted)
        if browser_pool:
            logger.info("Starting browser pool")
            await browser_pool.__aenter__()

        # Guardrail check - evaluate query safety before starting research
        if USE_GUARDRAILS:
            logger.info("Running guardrail safety check")
            _emit_event("guardrail_started", {"stage_id": "guardrail_check"})

            guardrail_result, cancelled = await check_query_safety(query, stop_flag)

            if check_stop():
                _emit_event("stopped", {"has_data": len(state.extracted_content) > 0})
                return {"status": "stopped", "response": None, "sources": []}

            logger.info(
                "Guardrail check complete",
                acceptable=guardrail_result.is_acceptable,
                confidence=guardrail_result.confidence,
            )
            _emit_event(
                "guardrail_complete",
                {
                    "stage_id": "guardrail_check",
                    "is_acceptable": guardrail_result.is_acceptable,
                    "reason": guardrail_result.reason,
                    "confidence": guardrail_result.confidence,
                },
            )

            if not guardrail_result.is_acceptable:
                # Query rejected by guardrails
                logger.warning(
                    "Query rejected by guardrails", reason=guardrail_result.reason
                )
                _emit_event(
                    "guardrail_rejected",
                    {
                        "reason": guardrail_result.reason,
                        "confidence": guardrail_result.confidence,
                    },
                )
                return {
                    "status": "rejected",
                    "response": None,
                    "sources": [],
                    "rejection_reason": guardrail_result.reason,
                }

        _emit_progress(0, max_queries + 2)

        # Convert list to set for fast lookups
        seen_urls_set = set(state.seen_urls)

        logger.info("Running initial search for original query")
        initial_results, new_urls = await _search_and_filter(
            query,
            max_results,
            seen_urls_set,
            None,
            "search_filter_initial",
            check_stop,
            stop_flag,
        )

        # Add new URLs to state
        state.seen_urls.extend(new_urls)
        state.queries_executed.append(query)
        state.searches = initial_results
        logger.info("Initial search complete", result_count=len(initial_results))

        if check_stop():
            _emit_event("stopped", {"has_data": len(state.extracted_content) > 0})
            return {"status": "stopped", "response": None, "sources": []}

        await _scrape_and_extract_results(initial_results, state, check_stop, stop_flag)

        _emit_progress(1, max_queries + 2)

        requires_recency = await _iterative_query_rewriting(
            state, max_queries, max_results, check_stop, stop_flag
        )

        logger.info(
            "Query rewriting phase complete",
            content_sources=len(state.extracted_content),
        )
        final_response = await _generate_final_response(state, requires_recency)
        _emit_progress(max_queries + 2, max_queries + 2)

        was_stopped = check_stop()
        status = "stopped" if was_stopped else "complete"

        if was_stopped:
            logger.info("Research workflow stopped by user")
            _emit_event("stopped", {"has_data": len(state.extracted_content) > 0})
        else:
            logger.info("Research workflow completed successfully")

        _emit_event("complete", {"response": final_response})

        return {
            "status": status,
            "response": final_response,
            "sources": [c.model_dump() for c in state.extracted_content],
        }
    finally:
        if browser_pool:
            logger.info("Closing browser pool")
            await browser_pool.__aexit__(None, None, None)
