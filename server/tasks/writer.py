"""Response writing task using LLM."""

from datetime import datetime
from typing import Any

from langgraph.func import task

from server.config import (
    WRITER_LLM_MODEL,
    WRITER_REASONING_EFFORT,
    MAX_CHARACTERS_PER_PAGE,
)
from server.prompts import load_prompt
from server.utils.util import create_task_llm, create_llm_messages, parse_content


@task
async def write_response_task(
    original_query: str,
    extracted_content_dicts: list[dict[str, Any]],
    requires_recency: bool = False,
) -> str:
    """Write a comprehensive response using LLM based on extracted content.

    Args:
        original_query: The original research query
        extracted_content_dicts: List of extracted content dictionaries
        requires_recency: Whether the topic requires current/recent information

    Returns:
        The generated response as a string
    """
    llm = create_task_llm(WRITER_LLM_MODEL, WRITER_REASONING_EFFORT, timeout=240.0)

    system_prompt = load_prompt("writer_system")

    # Build content summary for the prompt
    content_parts = []
    for content_dict in extracted_content_dicts:
        part = f"Source: [{content_dict['title']}]({content_dict['url']})\nType: {content_dict['page_type']}\n"
        if content_dict.get("name"):
            part += f"Name: {content_dict['name']}\n"
        if content_dict.get("content"):
            part += f"Content: {content_dict['content'][:MAX_CHARACTERS_PER_PAGE]}\n"
        elif content_dict.get("description"):
            part += f"Description: {content_dict['description']}\n"
        if content_dict.get("options"):
            part += f"Options: {', '.join(content_dict['options'][:10])}\n"
        if content_dict.get("features"):
            part += f"Features: {', '.join(content_dict['features'][:10])}\n"
        if content_dict.get("price"):
            part += f"Price: {content_dict['price']}\n"
        if content_dict.get("date"):
            part += f"Date: {content_dict['date']}\n"
        content_parts.append(part)

    # Build requirements section
    requirements = """Requirements:
1. Directly address the research question
2. Organize information logically
3. Include citations with [Title](URL) format for each source used
4. Be comprehensive but concise
5. Do NOT ask for follow up information such as "if you tell me X, I can Y", or explain what else you are capable of."""

    # Add recency instructions if topic requires current information
    if requires_recency:
        current_year = datetime.now().year
        requirements += f"""

IMPORTANT: This topic requires recent/current information. Today's date is {datetime.now().strftime("%Y-%m-%d")}.
- Prioritize content from {current_year} over older sources
- If a source contains mixed-date items (e.g., product listings), focus on the most recent entries
- Explicitly mention dates/years when citing time-sensitive information
- Do NOT include outdated prices, specs, or information when newer data is available
- If all available content is outdated, note this limitation in your response"""

    task_prompt = load_prompt("writer_task").format(
        original_query=original_query,
        content_parts="\n".join(content_parts),
        requirements=requirements,
    )

    messages = create_llm_messages(system_prompt, task_prompt)

    response = await llm.ainvoke(messages)

    return parse_content(response)
