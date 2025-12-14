import logging
from typing import Any

import structlog


def setup_logging() -> None:
    """Configure structlog for structured logging with contextvars support."""
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    pre_chain = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        timestamper,
    ]

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=pre_chain,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    structlog.configure(
        processors=pre_chain
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger with the given name."""
    return structlog.get_logger(name)


def bind_request_context(
    request_id: str | None = None, connection_id: str | None = None, **kwargs: Any
) -> None:
    """Bind request and connection identifiers into the structlog context."""
    context: dict[str, Any] = {
        "request_id": request_id or "unknown_request",
        "connection_id": connection_id or "unknown_connection",
    }
    context.update({k: v for k, v in kwargs.items() if v is not None})
    structlog.contextvars.bind_contextvars(**context)


def clear_request_context() -> None:
    """Clear any bound context variables."""
    structlog.contextvars.clear_contextvars()
