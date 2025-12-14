"""Guardrail task for checking query safety before research begins."""

from langgraph.func import task

from server.utils.util import (
    call_llm_with_cancel,
    create_task_llm,
    create_llm_messages,
    parse_json_response,
)
from server.config import GUARDRAIL_LLM_MODEL, GUARDRAIL_REASONING_EFFORT
from server.prompts import load_prompt
from server.utils.logging_config import get_logger

logger = get_logger(__name__)


class GuardrailResult:
    """Result from guardrail check."""

    def __init__(self, is_acceptable: bool, reason: str, confidence: float):
        self.is_acceptable = is_acceptable
        self.reason = reason
        self.confidence = confidence


@task
async def check_query_safety(
    query: str,
    stop_flag: dict[str, bool],
) -> tuple[GuardrailResult, bool]:
    """Check if a query is safe for research using LLM guardrail.

    Args:
        query: The search query to check
        stop_flag: Dictionary to signal task cancellation

    Returns:
        Tuple of (GuardrailResult, cancelled) where GuardrailResult contains safety assessment
    """
    llm = create_task_llm(GUARDRAIL_LLM_MODEL, GUARDRAIL_REASONING_EFFORT)

    system_prompt = load_prompt("guardrail_system")
    task_prompt = load_prompt("guardrail_task").format(query=query)

    messages = create_llm_messages(system_prompt, task_prompt)

    try:
        content, cancelled = await call_llm_with_cancel(stop_flag, llm, messages)
        if cancelled:
            return GuardrailResult(is_acceptable=True, reason="", confidence=0.0), True

        result = parse_json_response(content)

        is_acceptable = result.get("is_acceptable", True)  # Default to accept on parse error
        reason = result.get("reason", "Unable to determine")
        confidence = float(result.get("confidence", 0.5))

        logger.info(
            "Guardrail check for query",
            acceptable=is_acceptable,
            confidence=round(confidence, 2),
            reason=reason,
        )

        return GuardrailResult(
            is_acceptable=is_acceptable, reason=reason, confidence=confidence
        ), False

    except Exception as e:
        logger.error("Guardrail check failed", error=str(e), exc_info=True)
        # On error, default to accepting the query (fail open)
        return GuardrailResult(
            is_acceptable=True, reason="Unable to evaluate query safety", confidence=0.0
        ), False
