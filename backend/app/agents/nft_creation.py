"""LangGraph workflow for creator-confirmed fan NFT metadata and image drafts.

This Agent creates editable drafts only. Publishing, FAN fee checks, Pinata
pinning, and ERC-1155 writes are intentionally handled by the NFT service after
the creator confirms the form.
"""

import base64
import io
import re
from collections.abc import Mapping
from time import perf_counter
from typing import Any, Required, TypedDict

import httpx
from asgi_correlation_id import correlation_id
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from openai import AsyncOpenAI, OpenAIError
from pydantic import ValidationError

from app.agents.nft_visual_templates import NFT_METADATA_SYSTEM_PROMPT, NFT_METADATA_USER_PROMPT_TEMPLATE
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
    template_prompt: str | None
    selected_style_prompt: str | None
    preferred_name: str | None
    reference_notes: str | None
    reference_image_data_url: str | None
    iteration_image_data_url: str | None
    reference_image_urls: list[str]
    iteration_image_url: str | None
    generate_image: Required[bool]
    name: Required[str]
    description: Required[str]
    image_prompt: Required[str]
    suggested_attributes: Required[list[dict[str, str]]]
    metadata_source: Required[str]
    image_data_url: str | None
    image_source_url: str | None
    image_source: Required[str]
    image_error: str | None
    degraded: Required[bool]


def _image_log_value(value: Any) -> Any:
    """Keep image request logs useful without dumping multi-megabyte base64 data."""

    if isinstance(value, str) and value.startswith("data:image/"):
        header, _, encoded = value.partition(",")
        return f"<{header}; payload_chars={len(encoded)}>"
    if isinstance(value, io.BytesIO):
        return f"<file name={getattr(value, 'name', 'image')} bytes={value.getbuffer().nbytes}>"
    if isinstance(value, list):
        return [_image_log_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _image_log_value(item) for key, item in value.items()}
    return value


def _print_image_request(url: str, payload: dict[str, Any]) -> float:
    print(f"OPENAI_IMAGE_MODEL: {settings.openai_image_model}")
    print(f"Sending HTTP Request: POST {url}")
    print(f"request_id: {correlation_id.get() or None}")
    print(
        "Request options: "
        f"{_image_log_value({'method': 'post', 'url': url, 'headers': {'Authorization': 'Bearer ***'}, 'json_data': payload})}"
    )
    return perf_counter()


def _print_image_response(url: str, status_code: int, headers: Mapping[str, Any], started_at: float) -> None:
    reason = httpx.codes.get_reason_phrase(status_code)
    print(f'HTTP Response: POST {url} "{status_code} {reason}" Headers({dict(headers)})')
    print(f"OPENAI_IMAGE_MODEL elapsed_ms: {(perf_counter() - started_at) * 1000:.2f}")


def _image_endpoint(path: str) -> str:
    base_url = settings.openai_base_url.rstrip("/") or "https://api.openai.com/v1"
    return f"{base_url}/{path.lstrip('/')}"


def prepare_brief(state: NftCreationState) -> dict[str, Any]:
    """Normalize creator input before it reaches rules or a model prompt."""

    return {
        "theme": state["theme"].strip(),
        "story": state["story"].strip(),
        "visual_style": state["visual_style"].strip(),
        "template_prompt": (state.get("template_prompt") or "").strip() or None,
        "selected_style_prompt": (state.get("selected_style_prompt") or "").strip() or None,
        "preferred_name": (state.get("preferred_name") or "").strip() or None,
        "reference_notes": (state.get("reference_notes") or "").strip() or None,
        "reference_image_urls": state.get("reference_image_urls", []),
        "iteration_image_url": state.get("iteration_image_url"),
    }


def _reference_images(state: Mapping[str, Any], *, limit: int = 3) -> list[str]:
    """Order and deduplicate multimodal image inputs for image-edit models."""

    candidates = [
        state.get("reference_image_data_url"),
        *state.get("reference_image_urls", []),
        state.get("iteration_image_data_url"),
        state.get("iteration_image_url"),
    ]
    return list(dict.fromkeys(str(item) for item in candidates if item))[:limit]


def _siliconflow_reference_payload(references: list[str]) -> dict[str, str]:
    """Qwen Image Edit accepts up to three images as image/image2/image3."""

    return {
        "image" if index == 0 else f"image{index + 1}": reference
        for index, reference in enumerate(references[:3])
    }


async def _prepare_multimodal_references(
    references: list[str],
    http: httpx.AsyncClient,
) -> list[str]:
    """Send actual image bytes so the edit model cannot lose remote references."""

    prepared: list[str] = []
    for reference in references[:3]:
        if reference.startswith("data:image/"):
            prepared.append(reference)
            continue
        try:
            response = await http.get(reference)
            response.raise_for_status()
            mime_type = response.headers.get("content-type", "image/png").split(";", 1)[0]
            if mime_type not in {"image/jpeg", "image/png", "image/webp"}:
                raise ValueError(f"Unsupported reference image type: {mime_type}")
            encoded = base64.b64encode(response.content).decode("ascii")
            prepared.append(f"data:{mime_type};base64,{encoded}")
        except (httpx.HTTPError, ValueError) as error:
            logger.warning(
                "fan_nft_reference_download_fallback",
                error_type=type(error).__name__,
                reference_host=httpx.URL(reference).host,
            )
            prepared.append(reference)
    return prepared


def _prioritized_image_prompt(state: Mapping[str, Any]) -> str:
    template_prompt = str(state.get("template_prompt") or "").strip()
    selected_style_prompt = str(state.get("selected_style_prompt") or state.get("visual_style") or "").strip()
    artifact_prompt = str(state.get("image_prompt") or "").strip()
    sections = [
        "PROMPT PRIORITY IS STRICT. PRIORITY 1 is the mandatory combined visual constraint: the template defines the "
        "artwork form and composition, while the selected visual style defines how the entire artwork is rendered. "
        "Reconcile and preserve both completely. Lower-priority narrative instructions must never replace or dilute it.",
    ]
    if template_prompt or selected_style_prompt:
        priority_one_parts: list[str] = []
        if selected_style_prompt:
            priority_one_parts.append(
                "Render the complete artwork in this exact user-selected visual style; do not substitute a generic NFT "
                f"aesthetic: {selected_style_prompt}"
            )
        if template_prompt:
            priority_one_parts.append(
                "Apply this template's composition, collectible format, craft language, visual motifs, and art direction "
                f"visibly and literally: {template_prompt}"
            )
        sections.append(
            "PRIORITY 1 - VISUAL TEMPLATE + USER-SELECTED VISUAL STYLE (mandatory): "
            + " ".join(priority_one_parts)
        )
    if artifact_prompt:
        sections.append(
            "PRIORITY 2 - CURRENT NFT DETAILS: Integrate these subject, emotion, lighting, material, and story details "
            f"inside the combined PRIORITY 1 constraint: {artifact_prompt}"
        )
    return "\n\n".join(sections)[:7000]


def _reference_locked_image_prompt(prompt: str, references: list[str]) -> str:
    if not references:
        return prompt
    return (
        f"{prompt}\n\n"
        "REFERENCE EXECUTION RULE (mandatory): Use the supplied reference image as the primary visual source of truth "
        "within the selected template and style. "
        "Preserve its recognizable subject family and repeated motifs, composition density and spatial rhythm, "
        "silhouette language, linework, palette relationships, contrast, and emotional energy. "
        "Apply the requested NFT or merchandise format around those recognizable visual traits. "
        "Do not replace the reference's main motifs with an unrelated single emblem, animal, guardian, statue, "
        "landscape, or abstract symbol unless the user explicitly requests that replacement."
    )[:8000]


def _siliconflow_generation_payload(
    *,
    model: str,
    prompt: str,
    image_size: str,
    negative_prompt: str,
    references: list[str],
) -> dict[str, Any]:
    """Build a provider-valid payload, including Qwen Edit multimodal fields."""

    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
    }
    if "Qwen-Image-Edit" in model:
        payload.update({"num_inference_steps": 20, "guidance_scale": 4})
    else:
        payload.update({"image_size": image_size, "batch_size": 1})
    payload.update(_siliconflow_reference_payload(references))
    return payload


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


def _compact_nft_name(value: str) -> str:
    """Keep generated Chinese collectible names short and shelf-readable."""

    compact = re.split(r"[·|｜:：—-]", value.strip(), maxsplit=1)[0].strip()
    if re.search(r"[\u4e00-\u9fff]", compact) and len(compact) > 8:
        compact = compact[:8]
    return compact or value.strip()[:8]


def _non_event_image_prompt(image_prompt: str) -> str:
    """Prevent a generic admiration story from becoming an invented live event."""

    return (
        f"{image_prompt}\n\nThis is a personal, non-event fan keepsake inspired by personality, music atmosphere, "
        "an imagined scene, daily companionship, or an emotional symbol. Depict portrait-free symbolic memorabilia, "
        "a stylized environmental scene, a soft color field, or an original mascot-like emblem. It is not a concert or sports event: no stadium, "
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
        "Create a square portrait-free fan collectible about sincere admiration and personal fandom. "
        f"The story explicitly centers on {subject}. Translate personality, music atmosphere, imagined scenery, daily companionship, "
        "or emotional symbolism into an original emblem, environmental vignette, color field, or abstract memorabilia; "
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
        "recognizable visual identity, and successful material details unless the user explicitly asks to replace them. "
        "Improve the artwork as a coherent NFT or fan-merch collectible rather than changing to an unrelated concept. "
        "Apply the latest story and art-direction change: "
        f"{request}.\n\nBase artwork direction: {image_prompt}"
    )[:1500]


def build_nft_creation_graph(model_service: LLMService = llm_service) -> CompiledStateGraph:
    async def draft_metadata(state: NftCreationState) -> dict[str, Any]:
        """Generate collection metadata text, falling back to the rule draft."""

        fallback = _rule_draft(state)
        if not model_service.available:
            return fallback
        messages = [
            SystemMessage(content=NFT_METADATA_SYSTEM_PROMPT),
            HumanMessage(
                content=NFT_METADATA_USER_PROMPT_TEMPLATE.format(
                    theme=state["theme"],
                    story=state["story"],
                    visual_style=state["visual_style"],
                    preferred_name=state.get("preferred_name") or "无",
                    reference_notes=state.get("reference_notes") or "无",
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
            if state.get("iteration_image_data_url") or state.get("iteration_image_url"):
                image_prompt = _revision_image_prompt(image_prompt, state.get("reference_notes"))
            return {
                "name": _compact_nft_name(result.name),
                "description": result.description,
                "image_prompt": image_prompt,
                "suggested_attributes": [item.model_dump() for item in result.suggested_attributes],
                "metadata_source": "llm",
                "degraded": False,
            }
        except (LLMUnavailable, ValidationError, KeyError, TypeError, ValueError):
            logger.exception("fan_nft_metadata_draft_fallback")
            if state.get("iteration_image_data_url") or state.get("iteration_image_url"):
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
            reference_images = _reference_images(state)
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
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(30, connect=10),
                    follow_redirects=True,
                    trust_env=False,
                ) as reference_http:
                    prepared_references = await _prepare_multimodal_references(reference_images, reference_http)
                async with httpx.AsyncClient(timeout=settings.image_generation_timeout_seconds) as http:
                    prioritized_prompt = _prioritized_image_prompt(state)
                    payload = _siliconflow_generation_payload(
                        model=settings.openai_image_model,
                        prompt=_reference_locked_image_prompt(prioritized_prompt, prepared_references),
                        image_size=settings.openai_image_size,
                        negative_prompt=negative_prompt,
                        references=prepared_references,
                    )
                    logger.info(
                        "fan_nft_multimodal_image_request",
                        model=settings.openai_image_model,
                        reference_count=len(prepared_references),
                        reference_transport="base64_data_url",
                    )
                    image_endpoint = _image_endpoint("images/generations")
                    started_at = _print_image_request(image_endpoint, payload)
                    generated = await http.post(
                        image_endpoint,
                        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                        json=payload,
                    )
                    _print_image_response(image_endpoint, generated.status_code, generated.headers, started_at)
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
                    "image_source_url": image_url,
                    "image_source": "siliconflow",
                    "image_error": None,
                }
            if reference_images:
                image_files: list[io.BytesIO] = []
                async with httpx.AsyncClient(timeout=settings.image_generation_timeout_seconds) as http:
                    for index, reference_image in enumerate(reference_images):
                        if reference_image.startswith("data:image/"):
                            header, encoded_reference = reference_image.split(",", 1)
                            mime_type = header[5:].split(";", 1)[0]
                            reference_content = base64.b64decode(encoded_reference, validate=True)
                        else:
                            remote_reference = await http.get(reference_image)
                            remote_reference.raise_for_status()
                            mime_type = remote_reference.headers.get("content-type", "image/png").split(";", 1)[0]
                            reference_content = remote_reference.content
                        extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}.get(
                            mime_type, "png"
                        )
                        image_file = io.BytesIO(reference_content)
                        image_file.name = f"fanora-reference-{index + 1}.{extension}"
                        image_files.append(image_file)
                image_endpoint = _image_endpoint("images/edits")
                request_payload = {
                    "model": settings.openai_image_model,
                    "image": image_files,
                    "prompt": _reference_locked_image_prompt(_prioritized_image_prompt(state), reference_images),
                    "size": settings.openai_image_size,
                    "n": 1,
                    "response_format": "b64_json",
                    "input_fidelity": "high",
                }
                started_at = _print_image_request(image_endpoint, request_payload)
                raw_response = await client.images.with_raw_response.edit(
                    model=settings.openai_image_model,
                    image=image_files,
                    prompt=request_payload["prompt"],
                    size=settings.openai_image_size,
                    n=1,
                    response_format="b64_json",
                    input_fidelity="high",
                )
                _print_image_response(image_endpoint, raw_response.status_code, raw_response.headers, started_at)
                response = raw_response.parse()
            else:
                image_endpoint = _image_endpoint("images/generations")
                request_payload = {
                    "model": settings.openai_image_model,
                    "prompt": _prioritized_image_prompt(state),
                    "size": settings.openai_image_size,
                    "n": 1,
                    "response_format": "b64_json",
                }
                started_at = _print_image_request(image_endpoint, request_payload)
                raw_response = await client.images.with_raw_response.generate(
                    model=settings.openai_image_model,
                    prompt=request_payload["prompt"],
                    size=settings.openai_image_size,
                    n=1,
                    response_format="b64_json",
                )
                _print_image_response(image_endpoint, raw_response.status_code, raw_response.headers, started_at)
                response = raw_response.parse()
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
                "image_source_url": image_url,
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
            image_source_url=result.get("image_source_url"),
            metadata_source=result.get("metadata_source", "rules"),
            image_source=result.get("image_source", "unavailable"),
            degraded=bool(result.get("degraded")),
            image_error=result.get("image_error"),
        )


nft_creation_agent = NftCreationAgent()
