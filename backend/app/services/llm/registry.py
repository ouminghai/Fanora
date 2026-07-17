"""Lazy registry for OpenAI and OpenAI-compatible model endpoints."""

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from app.core.config import Settings, settings


class LLMRegistry:
    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    @property
    def model_names(self) -> list[str]:
        return self.settings.llm_models

    def build(self, model_name: str, **overrides) -> ChatOpenAI:
        if model_name not in self.model_names:
            raise ValueError(f"Unknown model '{model_name}'. Configured models: {', '.join(self.model_names)}")
        kwargs = {
            "model": model_name,
            "api_key": SecretStr(self.settings.openai_api_key),
            "temperature": self.settings.llm_temperature,
            "max_tokens": self.settings.llm_max_tokens,
            "max_retries": 0,
        }
        if self.settings.openai_base_url:
            kwargs["base_url"] = self.settings.openai_base_url
        kwargs.update(overrides)
        return ChatOpenAI(**kwargs)


llm_registry = LLMRegistry()
