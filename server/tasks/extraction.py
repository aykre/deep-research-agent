"""Content extraction task using LLM."""

import asyncio
from typing import Any

from langgraph.config import get_stream_writer
from langgraph.func import task

from server.config import (
    EXTRACTOR_LLM_MODEL,
    EXTRACTOR_REASONING_EFFORT,
    USE_PLAYWRIGHT,
    MAX_CHARACTERS_PER_PAGE,
)
from server.models import (
    ArticleContent,
    DirectoryContent,
    DirectoryItem,
    ExtractedContent,
    ForumPostContent,
    OtherContent,
    ProductContent,
)
from server.prompts import load_prompt
from server.services.scraper import scrape_page
from server.utils.logging_config import get_logger
from server.utils.util import (
    call_llm_with_cancel_raw,
    create_task_llm,
    create_llm_messages,
)

logger = get_logger(__name__)


# Tool schema for post_page_content
POST_PAGE_CONTENT_TOOL = {
    "type": "function",
    "function": {
        "name": "post_page_content",
        "description": (
            "Submit extracted page content with its classification. "
            "page_type must be one of: article, product, forum_post, directory, other. "
            "page_data must include 'title' and 'url', plus type-specific fields."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "page_type": {
                    "type": "string",
                    "enum": ["article", "product", "forum_post", "directory", "other"],
                    "description": "The type of page being submitted",
                },
                "page_data": {
                    "type": "object",
                    "description": "The extracted page data",
                    "properties": {
                        "title": {"type": "string"},
                        "url": {"type": "string"},
                        "content": {"type": "string"},
                        "author": {"type": "string"},
                        "date": {"type": "string"},
                        "name": {"type": "string"},
                        "price": {"type": "string"},
                        "description": {"type": "string"},
                        "options": {"type": "array", "items": {"type": "string"}},
                        "features": {"type": "array", "items": {"type": "string"}},
                        "replies": {"type": "array", "items": {"type": "string"}},
                        "items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "url": {"type": "string"},
                                    "description": {"type": "string"},
                                    "price": {"type": "string"},
                                },
                            },
                        },
                    },
                    "required": ["title", "url"],
                },
            },
            "required": ["page_type", "page_data"],
        },
    },
}


def _emit_scrape_event(
    stage_id: str, url: str, success: bool, error: str | None = None
) -> None:
    """Emit a scrape_complete event."""
    writer = get_stream_writer()
    writer(
        {
            "type": "scrape_complete",
            "data": {
                "stage_id": stage_id,
                "url": url,
                "success": success,
                "error": error,
            },
        }
    )


def _emit_extraction_started_event(stage_id: str, url: str) -> None:
    """Emit an extraction_started event."""
    writer = get_stream_writer()
    writer(
        {
            "type": "extraction_started",
            "data": {
                "stage_id": stage_id,
                "url": url,
            },
        }
    )


async def _scrape_with_timeout(
    url: str, timeout: float = 30.0
) -> tuple[str | None, str | None]:
    """Scrape a URL with timeout.

    Returns:
        Tuple of (content, error). One will be None.
    """
    try:
        content = await asyncio.wait_for(
            scrape_page(url, use_playwright=USE_PLAYWRIGHT),
            timeout=timeout,
        )
        return content, None
    except asyncio.TimeoutError:
        return None, f"Scraping timed out after {timeout} seconds"
    except Exception as e:
        return None, f"Scraping failed: {str(e)}"


async def _extract_content_with_llm(
    url: str,
    title: str,
    raw_content: str,
    stop_flag: dict[str, bool],
) -> tuple[ExtractedContent | None, str | None, bool]:
    """Extract structured content from raw HTML using LLM.

    Returns:
        Tuple of (extracted_content, error, cancelled)
    """
    # Reduce content size for faster processing
    truncated_content = raw_content[:MAX_CHARACTERS_PER_PAGE]
    logger.info("Truncated content", characters=len(truncated_content))

    llm = create_task_llm(EXTRACTOR_LLM_MODEL, EXTRACTOR_REASONING_EFFORT)
    llm_with_tools = llm.bind_tools([POST_PAGE_CONTENT_TOOL])

    system_prompt = load_prompt("extraction_system")
    task_prompt = load_prompt("extraction_task").format(
        url=url,
        title=title,
        content=truncated_content,
    )

    messages = create_llm_messages(system_prompt, task_prompt)

    logger.info("Sending extraction request to LLM", url=url)
    response, cancelled = await call_llm_with_cancel_raw(
        stop_flag, llm_with_tools, messages
    )

    if cancelled:
        return None, None, True

    # Parse tool call from response
    if response and response.tool_calls:
        tool_call = response.tool_calls[0]
        page_type = tool_call["args"].get("page_type", "other")
        page_data = tool_call["args"].get("page_data", {})

        # Ensure url and title are present
        page_data["url"] = url
        page_data["title"] = title

        extracted = create_extracted_content(page_type, page_data)
        logger.info("Successfully extracted content", url=url, page_type=page_type)
        return extracted, None, False
    else:
        logger.warning("LLM did not return tool calls", url=url)
        return None, "No content extracted by LLM", False


def create_extracted_content(
    page_type: str, page_data: dict[str, Any]
) -> ExtractedContent:
    """Factory function to create the right content type."""
    # Ensure required fields
    title = page_data.get("title", "Untitled")
    url = page_data.get("url", "")

    if page_type == "article":
        return ArticleContent(
            title=title,
            url=url,
            content=page_data.get("content", ""),
            author=page_data.get("author"),
            date=page_data.get("date"),
        )
    elif page_type == "product":
        # Sanitize features - ensure they are strings, not dicts
        raw_features = page_data.get("features", [])
        features = []
        for feature in raw_features:
            if isinstance(feature, str):
                features.append(feature)
            elif isinstance(feature, dict):
                # Convert dict to string representation
                features.append(str(feature))
        raw_options = page_data.get("options", [])
        options = []
        for option in raw_options:
            if isinstance(option, str):
                options.append(option)
            elif isinstance(option, dict):
                # Convert dict to string representation
                options.append(str(option))

        return ProductContent(
            name=page_data.get("name"),
            title=title,
            url=url,
            price=page_data.get("price"),
            description=page_data.get("description"),
            options=options,
            features=features,
        )
    elif page_type == "forum_post":
        return ForumPostContent(
            title=title,
            url=url,
            content=page_data.get("content", ""),
            author=page_data.get("author"),
            replies=page_data.get("replies", []),
        )
    elif page_type == "directory":
        items = []
        for item in page_data.get("items", []):
            items.append(
                DirectoryItem(
                    title=item.get("title", ""),
                    url=item.get("url"),
                    description=item.get("description"),
                    price=item.get("price"),
                )
            )
        return DirectoryContent(title=title, url=url, items=items)
    else:
        return OtherContent(
            title=title,
            url=url,
            content=page_data.get("content", ""),
        )


@task
async def scrape_and_extract_task(
    url: str, title: str, stop_flag: dict[str, bool]
) -> tuple[dict[str, Any], bool]:
    """Scrape and extract content from a URL using LLM.

    Args:
        url: The URL to scrape and extract content from
        title: The title of the page
        stop_flag: Dictionary to signal task cancellation

    Returns:
        Tuple of (result_dict, cancelled) where result_dict contains scrape and extraction results
    """
    import time

    scrape_stage_id = f"scrape_{url}"
    extract_stage_id = f"extract_{url}"

    result = {
        "url": url,
        "title": title,
        "success": False,
        "extracted": None,
        "error": None,
        "extraction_error": None,
    }

    try:
        # Scrape the page
        start_time = time.time()
        logger.info("Starting scrape", url=url)

        raw_content, scrape_error = await _scrape_with_timeout(url)

        if scrape_error:
            logger.error("Scraping failed", url=url, error=scrape_error)
            result["error"] = scrape_error
            _emit_scrape_event(scrape_stage_id, url, success=False, error=scrape_error)
            return result, False

        # Scrape successful
        scrape_duration = time.time() - start_time
        result["success"] = True
        logger.info(
            "Successfully scraped page",
            url=url,
            duration_seconds=round(scrape_duration, 2),
            content_length=len(raw_content),  # type: ignore[arg-type]
        )
        _emit_scrape_event(scrape_stage_id, url, success=True)

        # Extract content with LLM
        _emit_extraction_started_event(extract_stage_id, url)
        logger.info("Starting extraction", url=url, model=EXTRACTOR_LLM_MODEL)

        try:
            extraction_start = time.time()
            extracted, extraction_error, cancelled = await _extract_content_with_llm(
                url,
                title,
                raw_content,  # type: ignore
                stop_flag,
            )

            if cancelled:
                return result, True

            extraction_duration = time.time() - extraction_start
            logger.info(
                "Received LLM response",
                url=url,
                duration_seconds=round(extraction_duration, 2),
            )

            if extracted:
                result["extracted"] = extracted.model_dump()
            else:
                result["extraction_error"] = extraction_error

        except asyncio.TimeoutError:
            logger.error("Extraction timed out", url=url)
            result["extraction_error"] = "Extraction timed out after 60 seconds"
        except Exception as extract_error:
            logger.error(
                "Extraction failed", url=url, error=str(extract_error), exc_info=True
            )
            result["extraction_error"] = f"Extraction failed: {str(extract_error)}"

    except Exception as e:
        logger.error(
            "Unexpected error in scrape_and_extract_task",
            url=url,
            error=str(e),
            exc_info=True,
        )
        result["success"] = False
        result["error"] = f"Unexpected error: {str(e)}"

    return result, False
