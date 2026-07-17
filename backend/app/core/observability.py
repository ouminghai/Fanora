"""Optional Langfuse callbacks without a hard runtime dependency."""

from typing import Any

from app.core.config import settings
from app.core.logging import logger


def get_llm_callbacks() -> list[Any]:
    if not settings.langfuse_enabled:
        return []
    try:
        from langfuse.langchain import CallbackHandler

        return [CallbackHandler()]
    except Exception:
        logger.exception("langfuse_callback_unavailable")
        return []
