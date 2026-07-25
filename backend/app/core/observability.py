"""Optional Langfuse callbacks without a hard runtime dependency."""

import importlib
from typing import Any

from app.core.config import settings
from app.core.logging import logger

_callback_factory: Any | None = None
_callback_lookup_complete = False


def _load_callback_factory() -> Any | None:
    global _callback_factory, _callback_lookup_complete
    if _callback_lookup_complete:
        return _callback_factory
    try:
        module = importlib.import_module("langfuse.langchain")
        _callback_factory = module.CallbackHandler
    except (ImportError, AttributeError) as error:
        logger.warning("langfuse_callback_unavailable", error_type=type(error).__name__)
        _callback_factory = None
    finally:
        _callback_lookup_complete = True
    return _callback_factory


def get_llm_callbacks() -> list[Any]:
    if not settings.langfuse_enabled:
        return []
    callback_factory = _load_callback_factory()
    if callback_factory is None:
        return []
    try:
        return [callback_factory()]
    except Exception as error:
        logger.warning("langfuse_callback_initialization_failed", error_type=type(error).__name__)
        return []
