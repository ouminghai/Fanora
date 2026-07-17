"""LLM calls with structured output, retry, fallback, and timeout budgets."""

import asyncio
import time
from typing import Any, TypeVar

from langchain_core.messages import BaseMessage
from openai import APIError, APITimeoutError, OpenAIError, RateLimitError
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import logger
from app.core.metrics import llm_inference_duration_seconds
from app.core.observability import get_llm_callbacks
from app.services.llm.registry import LLMRegistry, llm_registry

T = TypeVar("T", bound=BaseModel)


class LLMUnavailable(RuntimeError):
    pass


class LLMService:
    """Small interface hiding model provider, retry, and fallback details."""

    def __init__(self, registry: LLMRegistry = llm_registry) -> None:
        self.registry = registry

    @property
    def available(self) -> bool:
        return settings.llm_enabled and bool(self.registry.model_names)

    @retry(
        stop=stop_after_attempt(settings.llm_max_retries),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError, APIError)),
        reraise=True,
    )
    async def _invoke(self, runnable: Any, messages: list[BaseMessage], model_name: str) -> Any:
        started_at = time.perf_counter()
        try:
            return await runnable.ainvoke(messages, config={"callbacks": get_llm_callbacks()})
        finally:
            llm_inference_duration_seconds.labels(model_name).observe(time.perf_counter() - started_at)

    async def call_structured(self, messages: list[BaseMessage], response_model: type[T]) -> T:
        if not self.available:
            raise LLMUnavailable("No OpenAI-compatible model is configured")

        async def call_with_fallback() -> T:
            last_error: Exception | None = None
            for model_name in self.registry.model_names:
                try:
                    model = self.registry.build(model_name)
                    runnable = model.with_structured_output(response_model)
                    result = await self._invoke(runnable, messages, model_name)
                    return result
                except OpenAIError as error:
                    last_error = error
                    logger.warning("llm_model_failed", model=model_name, error_type=type(error).__name__)
            raise LLMUnavailable(f"All configured models failed: {last_error}")

        try:
            return await asyncio.wait_for(call_with_fallback(), timeout=settings.llm_total_timeout_seconds)
        except TimeoutError as error:
            raise LLMUnavailable("LLM total timeout budget exceeded") from error


llm_service = LLMService()
