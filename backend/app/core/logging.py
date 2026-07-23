"""Structured logging adapted from the upstream production template."""

import logging
import sys
from typing import Any

import structlog
from asgi_correlation_id import correlation_id
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.core.config import settings


def _add_request_id(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    request_id = correlation_id.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def setup_logging() -> None:
    """Configure console logs for local development and JSON logs for production."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level, force=True)
    for noisy_logger in ("httpcore", "httpx", "urllib3", "web3", "web3.RequestManager"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        _add_request_id,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def bind_log_context(**values: Any) -> None:
    bind_contextvars(**values)


def clear_log_context() -> None:
    clear_contextvars()


setup_logging()
logger = structlog.get_logger("fanora")
