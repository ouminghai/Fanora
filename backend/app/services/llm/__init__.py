"""OpenAI-compatible LLM infrastructure."""

from app.services.llm.service import LLMService, llm_service

__all__ = ["LLMService", "llm_service"]
