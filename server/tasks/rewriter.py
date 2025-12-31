"""Query rewriting task using LLM."""

from datetime import datetime

from langgraph.func import task

from server.utils.util import (
    call_llm_with_cancel,
    create_task_llm,
    create_llm_messages,
    parse_json_response,
)
from server.config import REWRITER_LLM_MODEL, REWRITER_REASONING_EFFORT
from server.models import SearchResult, QueryWithFilter, RewriterOutput
from server.prompts import load_prompt


def _build_content_summary(searches: list[SearchResult]) -> str:
    """Build a summary of extracted content for the rewriter."""
    if not searches:
        return "No content gathered yet."

    summaries = []
    for c in searches:
        summary = f"- [{c.title}]: {c.snippet[:250]}"
        summaries.append(summary)
    return "\n".join(summaries)


@task
async def rewrite_queries_task(
    original_query: str,
    queries_executed: list[str],
    content_summary: str,
    stop_flag: dict[str, bool],
    attempts: int = 0,
) -> tuple[RewriterOutput, bool]:
    """Rewrite search queries using LLM based on original query and content summary.

    Args:
        original_query: The original search query
        queries_executed: List of previously executed queries
        content_summary: Summary of extracted content
        stop_flag: Dictionary to signal task cancellation

    Returns:
        Tuple of (RewriterOutput, cancelled) where cancelled is True if task was cancelled
    """
    llm = create_task_llm(REWRITER_LLM_MODEL, REWRITER_REASONING_EFFORT)

    # Get current date for context
    today = datetime.now().strftime("%Y-%m-%d")
    current_year = datetime.now().year

    system_prompt = load_prompt("rewriter_system").format(
        today=today,
        current_year=current_year,
    )

    queries_executed_text = "\n".join(f"- {q}" for q in queries_executed)

    task_prompt = load_prompt("rewriter_task").format(
        original_query=original_query,
        queries_executed=queries_executed_text,
        content_summary=content_summary,
    )

    messages = create_llm_messages(system_prompt, task_prompt)

    content, cancelled = await call_llm_with_cancel(stop_flag, llm, messages)
    if cancelled:
        return RewriterOutput(action="cancelled"), True

    # Try to parse JSON response
    try:
        result = parse_json_response(content)

        if result.get("action") == "stop":
            return RewriterOutput(action="stop"), False

        queries = []
        for q in result.get("queries", [])[:3]:
            if isinstance(q, dict):
                queries.append(
                    QueryWithFilter(
                        query=q.get("query", ""),
                        time_filter=q.get("time_filter"),
                        strategy=q.get("strategy"),
                    )
                )
            elif isinstance(q, str):
                queries.append(
                    QueryWithFilter(query=q, time_filter=None, strategy=None)
                )

        return RewriterOutput(
            action="continue",
            requires_recency=result.get("requires_recency", False),
            queries=queries,
        ), False

    except Exception:
        # Fallback: parse as plain text
        if content.upper() == "STOP":
            return RewriterOutput(action="stop"), False

        if attempts > 0:
            raise RuntimeError("Error parsing rewrite response")

        return await rewrite_queries_task(
            original_query=original_query,
            queries_executed=queries_executed,
            content_summary=content_summary,
            stop_flag=stop_flag,
            attempts=attempts + 1,
        )
