import asyncio
import json
from typing import Any

from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable


async def call_llm_with_cancel(
    stop_flag: dict[str, bool], llm: ChatOpenAI, messages: LanguageModelInput
) -> tuple[str, bool]:
    task = asyncio.create_task(llm.ainvoke(messages))

    while not task.done():
        # Check stop flag
        if stop_flag.get("stopped"):
            task.cancel()
            try:
                await task  # Wait for cancellation to complete
            except asyncio.CancelledError:
                pass
            return "", True

        # Wait a short time before checking again
        await asyncio.sleep(0.3)

    # Task is done, get the result
    response = await task
    return parse_content(response), False


async def call_llm_with_cancel_raw(
    stop_flag: dict[str, bool],
    llm: Runnable[LanguageModelInput, AIMessage],
    messages: LanguageModelInput,
) -> tuple[AIMessage | None, bool]:
    task = asyncio.create_task(llm.ainvoke(messages))

    while not task.done():
        # Check stop flag
        if stop_flag.get("stopped"):
            task.cancel()
            try:
                await task  # Wait for cancellation to complete
            except asyncio.CancelledError:
                pass
            return None, True

        # Wait a short time before checking again
        await asyncio.sleep(0.3)

    # Task is done, get the result
    response = await task
    return response, False


def parse_content(response) -> str:
    # Handle response content (may be a list with reasoning models or a string)
    if isinstance(response.content, list):
        # Extract text content from reasoning model response
        content = ""
        for item in response.content:
            if isinstance(item, dict) and item.get("type") == "text":
                content = item.get("text", "")
                break
        content = content.strip()
    else:
        content = response.content.strip()  # type: ignore

    if content == "":
        meta = response.response_metadata

        if meta.get("status") != "completed":
            reason = None
            if "incomplete_details" in meta:
                reason = meta["incomplete_details"].get("reason")

            raise RuntimeError(
                f"LLM response not completed (status={meta.get('status')}, reason={reason})"
            )

        raise RuntimeError("LLM returned empty response")

    return content


def create_task_llm(
    model: str,
    reasoning_effort: str,
    temperature: float = 0,
    timeout: float = 50.0,
    max_retries: int = 0,
) -> ChatOpenAI:
    """Create a standardized ChatOpenAI instance for task execution.

    Args:
        model: The model name to use
        reasoning_effort: The reasoning effort level
        temperature: Temperature setting (default: 0)
        timeout: Timeout in seconds (default: 50.0)
        max_retries: Maximum retry attempts (default: 0)

    Returns:
        Configured ChatOpenAI instance
    """
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        reasoning={"effort": reasoning_effort},
        timeout=timeout,
        max_retries=max_retries,
    )


def extract_json_from_markdown(content: str) -> str:
    """Extract JSON content from markdown code blocks.

    Handles responses that may be wrapped in ```json or ``` blocks.

    Args:
        content: The raw content that may contain markdown code blocks

    Returns:
        Cleaned content with markdown wrapper removed
    """
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
        content = content.strip()
    return content


def parse_json_response(content: str) -> dict[str, Any]:
    """Parse JSON response with automatic markdown extraction.

    Args:
        content: Raw content that may contain JSON in markdown blocks

    Returns:
        Parsed JSON as a dictionary

    Raises:
        json.JSONDecodeError: If content is not valid JSON after extraction
    """
    cleaned_content = extract_json_from_markdown(content)
    return json.loads(cleaned_content)


def create_llm_messages(system_prompt: str, task_prompt: str) -> list:
    """Create standard LLM message list with system and human messages.

    Args:
        system_prompt: The system prompt content
        task_prompt: The task/human prompt content

    Returns:
        List containing SystemMessage and HumanMessage
    """
    return [
        SystemMessage(content=system_prompt),
        HumanMessage(content=task_prompt),
    ]
