import pytest
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from app.core.config import settings
from app.services.llm.service import LLMService, LLMUnavailable


class StructuredDraft(BaseModel):
    name: str
    description: str


class FakeModel:
    def __init__(self, content: str) -> None:
        self.content = content

    async def ainvoke(self, messages, config=None):
        del messages, config
        return AIMessage(content=self.content)


class FakeRegistry:
    model_names = ["primary-model", "fallback-model"]

    def build(self, model_name: str) -> FakeModel:
        if model_name == "primary-model":
            return FakeModel('{"name": "花海回声"\n"description": "缺少逗号的响应"}')
        return FakeModel('{"name": "花海回声", "description": "备用模型的合法响应"}')


class AllMalformedRegistry:
    model_names = ["primary-model", "fallback-model"]

    def build(self, model_name: str) -> FakeModel:
        return FakeModel(f'{{"name": "{model_name}"\n"description": "缺少逗号的响应"}}')


async def test_structured_call_uses_fallback_model_when_primary_returns_malformed_json(monkeypatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_base_url", "https://api.siliconflow.cn/v1")
    service = LLMService(FakeRegistry())

    result = await service.call_structured([HumanMessage(content="draft metadata")], StructuredDraft)

    assert result == StructuredDraft(name="花海回声", description="备用模型的合法响应")


async def test_structured_call_wraps_format_errors_after_all_models_fail(monkeypatch) -> None:
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_base_url", "https://api.siliconflow.cn/v1")
    service = LLMService(AllMalformedRegistry())

    with pytest.raises(LLMUnavailable, match="All configured models failed: Expecting ',' delimiter"):
        await service.call_structured([HumanMessage(content="draft metadata")], StructuredDraft)
