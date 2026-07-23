"""LangGraph workflow for creator-confirmed fan NFT metadata and image drafts."""

import base64
from typing import Any, Required, TypedDict

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from openai import AsyncOpenAI, OpenAIError
from pydantic import ValidationError

from app.core.config import settings
from app.core.logging import logger
from app.schemas.nft_agent import NftDraftRequest, NftDraftResponse, NftMetadataNarrative
from app.services.llm import LLMService, llm_service
from app.services.llm.service import LLMUnavailable


class NftCreationState(TypedDict, total=False):
    theme: Required[str]
    story: Required[str]
    visual_style: Required[str]
    preferred_name: str | None
    reference_notes: str | None
    generate_image: Required[bool]
    name: Required[str]
    description: Required[str]
    image_prompt: Required[str]
    suggested_attributes: Required[list[dict[str, str]]]
    metadata_source: Required[str]
    image_data_url: str | None
    image_source: Required[str]
    image_error: str | None
    degraded: Required[bool]


def prepare_brief(state: NftCreationState) -> dict[str, Any]:
    return {
        "theme": state["theme"].strip(),
        "story": state["story"].strip(),
        "visual_style": state["visual_style"].strip(),
        "preferred_name": (state.get("preferred_name") or "").strip() or None,
        "reference_notes": (state.get("reference_notes") or "").strip() or None,
    }


def _rule_draft(state: NftCreationState) -> dict[str, Any]:
    name = state.get("preferred_name") or f"{state['theme']} · Fanora Limited"
    story = state["story"].strip()
    description = story if len(story) <= 1000 else f"{story[:997]}..."
    reference = f" Reference notes: {state['reference_notes']}." if state.get("reference_notes") else ""
    image_prompt = (
        f"Create a square collectible NFT artwork about {state['theme']}. "
        f"Visual style: {state['visual_style']}. Story and emotional context: {story}."
        f"{reference} Premium music memorabilia, original composition, no logos, no watermark, no readable text."
    )[:1500]
    return {
        "name": name[:100],
        "description": description,
        "image_prompt": image_prompt,
        "suggested_attributes": [
            {"trait_type": "Theme", "value": state["theme"][:120]},
            {"trait_type": "Edition", "value": "Fan Limited"},
        ],
        "metadata_source": "rules",
        "degraded": False,
    }


def build_nft_creation_graph(model_service: LLMService = llm_service) -> CompiledStateGraph:
    async def draft_metadata(state: NftCreationState) -> dict[str, Any]:
        fallback = _rule_draft(state)
        if not model_service.available:
            return fallback
        messages = [
            SystemMessage(
                content=(
                    "你为 Fanora 创作者生成 ERC-1155 限量粉丝 NFT 草稿。返回名称、描述、图片提示词和公开属性。"
                    "不要决定价格、供应量、发行资格，不要声称已经发布、固定到 IPFS 或完成铸造。"
                    "图片提示词应形成原创方形收藏品构图，避免品牌 Logo、水印和可读文字。"
                )
            ),
            HumanMessage(
                content=(
                    f"主题：{state['theme']}\n粉丝故事：{state['story']}\n视觉风格：{state['visual_style']}\n"
                    f"名称偏好：{state.get('preferred_name') or '无'}\n参考说明：{state.get('reference_notes') or '无'}"
                )
            ),
        ]
        try:
            result = await model_service.call_structured(messages, NftMetadataNarrative)
            return {
                "name": result.name,
                "description": result.description,
                "image_prompt": result.image_prompt,
                "suggested_attributes": [item.model_dump() for item in result.suggested_attributes],
                "metadata_source": "llm",
                "degraded": False,
            }
        except (LLMUnavailable, ValidationError, KeyError, TypeError, ValueError):
            logger.exception("fan_nft_metadata_draft_fallback")
            return {**fallback, "degraded": True}

    async def generate_image(state: NftCreationState) -> dict[str, Any]:
        if not state.get("generate_image", True):
            return {"image_data_url": None, "image_source": "not_requested", "image_error": None}
        if not settings.openai_api_key or not settings.openai_image_model:
            return {
                "image_data_url": None,
                "image_source": "unavailable",
                "image_error": "OpenAI image generation is not configured",
                "degraded": True,
            }
        client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url or None,
            timeout=settings.image_generation_timeout_seconds,
        )
        try:
            response = await client.images.generate(
                model=settings.openai_image_model,
                prompt=state["image_prompt"],
                size=settings.openai_image_size,
                n=1,
            )
            item = response.data[0]
            encoded = getattr(item, "b64_json", None)
            if not encoded and getattr(item, "url", None):
                async with httpx.AsyncClient(timeout=settings.image_generation_timeout_seconds) as http:
                    remote = await http.get(item.url)
                    remote.raise_for_status()
                    encoded = base64.b64encode(remote.content).decode("ascii")
            if not encoded:
                raise RuntimeError("Image generation response did not include image data")
            return {
                "image_data_url": f"data:image/png;base64,{encoded}",
                "image_source": "openai",
                "image_error": None,
            }
        except (OpenAIError, httpx.HTTPError, RuntimeError) as error:
            logger.exception("fan_nft_image_generation_failed", error_type=type(error).__name__)
            return {
                "image_data_url": None,
                "image_source": "unavailable",
                "image_error": "Image generation failed; upload an image or retry later",
                "degraded": True,
            }

    workflow = StateGraph(NftCreationState)
    workflow.add_node("prepare_brief", prepare_brief)
    workflow.add_node("draft_metadata", draft_metadata)
    workflow.add_node("generate_image", generate_image)
    workflow.add_edge(START, "prepare_brief")
    workflow.add_edge("prepare_brief", "draft_metadata")
    workflow.add_edge("draft_metadata", "generate_image")
    workflow.add_edge("generate_image", END)
    return workflow.compile()


class NftCreationAgent:
    def __init__(self, model_service: LLMService = llm_service) -> None:
        self._graph = build_nft_creation_graph(model_service)

    async def create_draft(self, request: NftDraftRequest) -> NftDraftResponse:
        result = await self._graph.ainvoke(request.model_dump())
        return NftDraftResponse(
            name=result["name"],
            description=result["description"],
            theme=result["theme"],
            image_prompt=result["image_prompt"],
            suggested_attributes=result["suggested_attributes"],
            image_data_url=result.get("image_data_url"),
            metadata_source=result.get("metadata_source", "rules"),
            image_source=result.get("image_source", "unavailable"),
            degraded=bool(result.get("degraded")),
            image_error=result.get("image_error"),
        )


nft_creation_agent = NftCreationAgent()
