"""Cloudflare Turnstile verification service."""

from typing import Any

import httpx

from server.config import TURNSTILE_SECRET_KEY, USE_TURNSTILE
from server.utils.logging_config import get_logger

logger = get_logger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile_token(token: str) -> bool:
    """Verify a Cloudflare Turnstile token.

    Args:
        token: The Turnstile token to verify

    Returns:
        True if verification succeeds, False otherwise
    """
    if not USE_TURNSTILE:
        # If Turnstile is disabled, always return True
        return True

    if not TURNSTILE_SECRET_KEY:
        logger.error("TURNSTILE_SECRET_KEY not configured while Turnstile enabled")
        return False

    if not token:
        logger.warning("Empty Turnstile token provided")
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload: dict[str, Any] = {
                "secret": TURNSTILE_SECRET_KEY,
                "response": token,
            }

            response = await client.post(TURNSTILE_VERIFY_URL, data=payload)
            response.raise_for_status()

            result = response.json()
            success = result.get("success", False)

            if not success:
                error_codes = result.get("error-codes", [])
                logger.warning("Turnstile verification failed", error_codes=error_codes)

            return success

    except httpx.HTTPError as e:
        logger.error("Turnstile verification HTTP error", error=str(e))
        return False
    except Exception as e:
        logger.error("Turnstile verification error", error=str(e), exc_info=True)
        return False
