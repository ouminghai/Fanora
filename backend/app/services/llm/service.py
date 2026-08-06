"""LLM calls with structured output, retry, fallback, and timeout budgets."""

import asyncio
import json
import re
import time
from collections.abc import Sequence
from json import JSONDecodeError
from typing import Any, TypeVar

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool
from openai import APIError, APITimeoutError, OpenAIError, RateLimitError
from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.logging import logger
from app.core.metrics import llm_inference_duration_seconds
from app.core.observability import get_llm_callbacks
from app.services.llm.registry import LLMRegistry, llm_registry

T = TypeVar("T", bound=BaseModel)


class LLMUnavailable(RuntimeError):
    pass


def _extract_json_object(value: str) -> dict[str, Any]:
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[index:])
        except JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise JSONDecodeError("No JSON object found in model response", text, 0)


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
                    # SiliconFlow documents JSON-object mode for compatible chat
                    # models. Its Qwen endpoint can stall on OpenAI's stricter
                    # json_schema/parse request used by LangChain's default.
                    if "api.siliconflow.cn" in settings.openai_base_url.lower():
                        raw_result = await self._invoke(model, messages, model_name)
                        content = raw_result.content
                        if isinstance(content, list):
                            content = "".join(
                                item.get("text", "") if isinstance(item, dict) else str(item) for item in content
                            )
                        if not isinstance(content, str):
                            raise ValueError("SiliconFlow returned a non-text structured response")
                        return response_model.model_validate(_extract_json_object(content))
                    else:
                        runnable = model.with_structured_output(response_model)
                        result = await self._invoke(runnable, messages, model_name)
                        return result
                except (OpenAIError, ValidationError, TypeError, ValueError) as error:
                    last_error = error
                    logger.warning("llm_model_failed", model=model_name, error_type=type(error).__name__)
            raise LLMUnavailable(f"All configured models failed: {last_error}")

        try:
            return await asyncio.wait_for(call_with_fallback(), timeout=settings.llm_total_timeout_seconds)
        except TimeoutError as error:
            raise LLMUnavailable("LLM total timeout budget exceeded") from error

    async def call_with_tools(self, messages: list[BaseMessage], tools: Sequence[BaseTool]) -> AIMessage:
        """Let a configured chat model choose from a bounded set of tools."""

        if not self.available:
            raise LLMUnavailable("No OpenAI-compatible model is configured")

        async def call_with_fallback() -> AIMessage:
            last_error: Exception | None = None
            for model_name in self.registry.model_names:
                try:
                    runnable = self.registry.build(model_name).bind_tools(list(tools))
                    result = await self._invoke(runnable, messages, model_name)
                    if not isinstance(result, AIMessage):
                        raise TypeError("Tool-enabled model returned a non-AI message")
                    return result
                except (OpenAIError, TypeError, ValueError) as error:
                    last_error = error
                    logger.warning("llm_tool_model_failed", model=model_name, error_type=type(error).__name__)
            raise LLMUnavailable(f"All configured tool models failed: {last_error}")

        try:
            return await asyncio.wait_for(call_with_fallback(), timeout=settings.llm_total_timeout_seconds)
        except TimeoutError as error:
            raise LLMUnavailable("LLM tool-call timeout budget exceeded") from error


llm_service = LLMService()
