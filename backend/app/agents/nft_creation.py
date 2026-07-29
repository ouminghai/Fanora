"""LangGraph workflow for creator-confirmed fan NFT metadata and image drafts.

This Agent creates editable drafts only. Publishing, FAN fee checks, Pinata
pinning, and ERC-1155 writes are intentionally handled by the NFT service after
the creator confirms the form.
"""

import base64
import io
import re
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
    """Draft state shared by metadata and optional image-generation nodes."""

    theme: Required[str]
    story: Required[str]
    visual_style: Required[str]
    preferred_name: str | None
    reference_notes: str | None
    reference_image_data_url: str | None
    iteration_image_data_url: str | None
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
    """Normalize creator input before it reaches rules or a model prompt."""

    return {
        "theme": state["theme"].strip(),
        "story": state["story"].strip(),
        "visual_style": state["visual_style"].strip(),
        "preferred_name": (state.get("preferred_name") or "").strip() or None,
        "reference_notes": (state.get("reference_notes") or "").strip() or None,
    }


def _rule_draft(state: NftCreationState) -> dict[str, Any]:
    """Build a usable deterministic draft when the model path is unavailable."""

    name = state.get("preferred_name") or f"{state['theme']} · Fanora Limited"
    story = state["story"].strip()
    description = story if len(story) <= 1000 else f"{story[:997]}..."
    reference_notes = state.get("reference_notes")
    reference = f" Reference notes: {reference_notes}." if reference_notes else ""
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


def _story_subjects(story: str) -> list[str]:
    """Extract explicitly named people from common fan phrasing."""

    return list(
        dict.fromkeys(
            re.findall(r"(?:喜欢|喜歡|支持|欣赏|欣賞|爱|愛)([\u4e00-\u9fff]{2,5})", story)
        )
    )


def _story_mentions_event(story: str) -> bool:
    return any(term in story for term in ("演唱会", "演出", "表演", "舞台", "现场", "观众", "票根"))


def _non_event_image_prompt(image_prompt: str) -> str:
    """Prevent a generic admiration story from becoming an invented live event."""

    return (
        f"{image_prompt}\n\nThis is a personal, non-event fan keepsake. Depict a portrait-free symbolic fan letter, "
        "soft color field, or intimate abstract memorabilia. It is not a concert or sports event: no stadium, "
        "arena, stage, venue, crowd, audience, performance, or live-show lighting."
    )[:1500]


def _story_grounded_draft(state: NftCreationState, fallback: dict[str, Any]) -> dict[str, Any]:
    """Prefer a faithful editable brief over fluent but unrelated copy."""

    story = state["story"]
    subjects = _story_subjects(story)
    subject = subjects[0] if subjects else "这份喜欢"
    fallback["name"] = (state.get("preferred_name") or f"写给{subject}的喜欢")[:100]
    fallback["description"] = (
        f"这份 NFT 记录的是：{story}。它不补写未发生的演出、现场或共同经历，"
        "只保留粉丝亲自表达的欣赏与情绪。"
    )[:1000]
    fallback["image_prompt"] = (
        "Create a square portrait-free fan-letter collectible about sincere admiration and personal fandom. "
        f"The story explicitly centers on {subject}. Use a gentle symbolic color field and intimate abstract memorabilia; "
        "do not invent a concert, crowd, ticket, performance, stadium, or event not stated in the story. "
        "Do not depict a real person's face, logo, watermark, or readable text."
    )
    fallback["suggested_attributes"] = [
        {"trait_type": "故事主角", "value": subject[:120]},
        {"trait_type": "情感", "value": "欣赏与喜欢"},
    ]
    fallback["metadata_source"] = "rules"
    fallback["degraded"] = True
    return fallback


def _brief_is_story_grounded(state: NftCreationState, result: NftMetadataNarrative) -> bool:
    """Reject generic English concert copy when it missed a Chinese fan story."""

    visible_brief = f"{result.name} {result.description}"
    story = state["story"]
    if re.search(r"[\u4e00-\u9fff]", story):
        if not re.search(r"[\u4e00-\u9fff]", result.name):
            return False
        if not re.search(r"[\u4e00-\u9fff]", visible_brief):
            return False
    event_terms = ("演唱会", "演出", "表演", "舞台", "现场", "观众", "票根")
    if not _story_mentions_event(story) and any(term in visible_brief for term in event_terms):
        return False
    return all(subject in visible_brief for subject in _story_subjects(story))


def _revision_image_prompt(image_prompt: str, revision_request: str | None) -> str:
    """Lock a refinement to the previous image instead of regenerating a new concept."""

    request = revision_request or "make only the requested visual adjustment"
    return (
        "IMAGE-TO-IMAGE REVISION. The supplied reference image is the source of truth. "
        "Preserve its main subject, scene type, camera angle, composition, horizon, focal point, "
        "and overall lighting. Keep this as a live concert stage with a crowd and stage lighting; "
        "do not replace it with an abstract corridor, gallery, architecture, geometric installation, "
        "or product mockup. Apply only this limited change: "
        f"{request}.\n\nBase artwork direction: {image_prompt}"
    )[:1500]


def build_nft_creation_graph(model_service: LLMService = llm_service) -> CompiledStateGraph:
    async def draft_metadata(state: NftCreationState) -> dict[str, Any]:
        """Generate collection metadata text, falling back to the rule draft."""

        fallback = _rule_draft(state)
        if not model_service.available:
            return fallback
        messages = [
            SystemMessage(
                content=(
                    "Return ONLY one valid JSON object. Use these exact English keys: "
                    "name, description, image_prompt, suggested_attributes. "
                    "suggested_attributes must be an array of objects with exactly trait_type and value. "
                    "Never translate or rename the JSON keys, even when the content is Chinese. "
                    "The story is the source of truth; the theme and style are only visual constraints. "
                    "Never invent a concert, live event, crowd, ticket, or shared memory unless the story says so. "
                    "If the story is Chinese, write name, description, and attributes in Simplified Chinese. "
                    "If a named person appears in the story, retain that exact name in the name or description. "
                    "The description must state the fan's actual feeling in two or three grounded sentences. "
                    "Use an English image_prompt for an original square collectible. Do not generate a real person's portrait, "
                    "logos, watermarks, or readable text. "
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
            if not _brief_is_story_grounded(state, result):
                logger.warning("fan_nft_metadata_draft_not_story_grounded")
                grounded_fallback = _story_grounded_draft(state, fallback)
                if not _story_mentions_event(state["story"]):
                    grounded_fallback["image_prompt"] = _non_event_image_prompt(grounded_fallback["image_prompt"])
                return grounded_fallback
            image_prompt = result.image_prompt
            if not _story_mentions_event(state["story"]):
                image_prompt = _non_event_image_prompt(image_prompt)
            if state.get("iteration_image_data_url"):
                image_prompt = _revision_image_prompt(image_prompt, state.get("reference_notes"))
            return {
                "name": result.name,
                "description": result.description,
                "image_prompt": image_prompt,
                "suggested_attributes": [item.model_dump() for item in result.suggested_attributes],
                "metadata_source": "llm",
                "degraded": False,
            }
        except (LLMUnavailable, ValidationError, KeyError, TypeError, ValueError):
            logger.exception("fan_nft_metadata_draft_fallback")
            if state.get("iteration_image_data_url"):
                fallback["image_prompt"] = _revision_image_prompt(
                    fallback["image_prompt"], state.get("reference_notes")
                )
            elif not _story_mentions_event(state["story"]):
                fallback["image_prompt"] = _non_event_image_prompt(fallback["image_prompt"])
            return {**fallback, "degraded": True}

    async def generate_image(state: NftCreationState) -> dict[str, Any]:
        """Optionally call the image model and return a data URL for form preview."""

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
            reference_image = state.get("iteration_image_data_url") or state.get("reference_image_data_url")
            is_siliconflow = "api.siliconflow.cn" in settings.openai_base_url.lower()
            if is_siliconflow:
                # SiliconFlow uses an OpenAI-like base URL, but its image endpoint
                # returns {"images": [{"url": ...}]} and accepts reference images
                # directly in the JSON body rather than through /images/edits.
                negative_prompt = (
                    "logo, watermark, readable text, real celebrity portrait, abstract neon corridor, "
                    "empty gallery, interior architecture, geometric installation, product mockup"
                )
                if not _story_mentions_event(state["story"]):
                    negative_prompt += ", concert, stadium, arena, stage, venue, crowd, audience, performance"
                payload: dict[str, Any] = {
                    "model": settings.openai_image_model,
                    "prompt": state["image_prompt"],
                    "image_size": settings.openai_image_size,
                    "batch_size": 1,
                    "negative_prompt": negative_prompt,
                }
                if reference_image:
                    payload["image"] = reference_image
                async with httpx.AsyncClient(timeout=settings.image_generation_timeout_seconds) as http:
                    generated = await http.post(
                        f"{settings.openai_base_url.rstrip('/')}/images/generations",
                        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                        json=payload,
                    )
                    generated.raise_for_status()
                    images = generated.json().get("images", [])
                    image_url = images[0].get("url") if images else None
                    if not image_url:
                        raise RuntimeError("SiliconFlow image response did not include a URL")
                    remote = await http.get(image_url)
                    remote.raise_for_status()
                encoded = base64.b64encode(remote.content).decode("ascii")
                return {
                    "image_data_url": f"data:image/png;base64,{encoded}",
                    "image_source": "siliconflow",
                    "image_error": None,
                }
            if reference_image:
                header, encoded_reference = reference_image.split(",", 1)
                mime_type = header[5:].split(";", 1)[0]
                extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(mime_type, "png")
                image_file = io.BytesIO(base64.b64decode(encoded_reference, validate=True))
                image_file.name = f"fanora-reference.{extension}"
                response = await client.images.edit(
                    model=settings.openai_image_model,
                    image=image_file,
                    prompt=state["image_prompt"],
                    size=settings.openai_image_size,
                    n=1,
                    response_format="b64_json",
                    input_fidelity="high",
                )
            else:
                response = await client.images.generate(
                    model=settings.openai_image_model,
                    prompt=state["image_prompt"],
                    size=settings.openai_image_size,
                    n=1,
                    response_format="b64_json",
                )
            if not response.data:
                raise RuntimeError("Image generation response did not include a result")
            item = response.data[0]
            encoded = getattr(item, "b64_json", None)
            image_url = getattr(item, "url", None)
            if not encoded and image_url:
                async with httpx.AsyncClient(timeout=settings.image_generation_timeout_seconds) as http:
                    remote = await http.get(image_url)
                    remote.raise_for_status()
                    encoded = base64.b64encode(remote.content).decode("ascii")
            if not encoded:
                raise RuntimeError("Image generation response did not include image data")
            return {
                "image_data_url": f"data:image/png;base64,{encoded}",
                "image_source": "openai",
                "image_error": None,
            }
        except (OpenAIError, httpx.HTTPError, RuntimeError, ValueError) as error:
            logger.exception("fan_nft_image_generation_failed", error_type=type(error).__name__)
            return {
                "image_data_url": None,
                "image_source": "unavailable",
                "image_error": "Image generation failed; upload an image or retry later",
                "degraded": True,
            }

    # The image node depends on the metadata prompt, but the graph still returns
    # a useful draft if image generation is disabled or fails.
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
    """Facade for the /nft/creations/ai-draft endpoint."""

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
