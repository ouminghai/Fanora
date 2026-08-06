"""LangGraph tools for selecting and saving NFT visual templates."""

import json
from typing import Any

from langchain_core.tools import tool
from langgraph.prebuilt import ToolRuntime

from app.agents.nft_creation import nft_creation_agent
from app.agents.nft_visual_templates import STYLE_PROMPTS
from app.core.database import database_service
from app.schemas.nft_agent import NftDraftRequest, NftDraftResponse, NftVisualTemplateCreate
from app.services.nft_visual_templates import nft_visual_template_service


def _tool_result(action: str, status: str, summary: str, **payload: Any) -> str:
    return json.dumps(
        {"action": action, "status": status, "summary": summary, **payload},
        ensure_ascii=False,
    )


@tool
async def select_visual_template(template_id: str, reason: str, runtime: ToolRuntime) -> str:
    """Select one accessible visual template recommended for the current story."""

    state = runtime.state
    user_id = str(state.get("user_id", ""))
    available_ids = {str(item.get("id")) for item in state.get("available_templates", [])}
    if not user_id or template_id not in available_ids:
        return _tool_result(
            "select_visual_template",
            "degraded",
            "推荐的视觉模板不可用，已保留当前模板。",
        )
    async with database_service.session() as session:
        template = await nft_visual_template_service.get_for_user(session, user_id, template_id)
    if template is None:
        return _tool_result(
            "select_visual_template",
            "degraded",
            "推荐的视觉模板不存在或无权访问，已保留当前模板。",
        )
    return _tool_result(
        "select_visual_template",
        "completed",
        f"LLM 推荐并切换到「{template.name}」：{reason.strip()}",
        template=template.model_dump(),
    )


@tool
async def save_visual_template(
    name: str,
    category: str,
    description: str,
    runtime: ToolRuntime,
) -> str:
    """Save the current generated NFT direction as a private reusable visual template."""

    state = runtime.state
    user_id = str(state.get("user_id", ""))
    draft = state.get("draft") or {}
    current_template = state.get("template") or {}
    references = list(
        dict.fromkeys(
            [
                state.get("last_image_url"),
                *state.get("reference_image_urls", []),
                *current_template.get("reference_image_urls", []),
            ]
        )
    )
    references = [str(item) for item in references if item][:6]
    if not user_id or not draft or not draft.get("image_prompt") or not references:
        return _tool_result(
            "save_visual_template",
            "degraded",
            "当前还没有可保存的生成版本，请先完成一轮图片生成。",
        )
    payload = NftVisualTemplateCreate(
        name=name.strip()[:80],
        category=category.strip()[:40],
        description=description.strip()[:500],
        prompt=str(draft["image_prompt"]),
        reference_image_urls=references,
        palette=list(current_template.get("palette", []))[:6],
        elements=list(current_template.get("elements", []))[:12],
        forbidden=list(current_template.get("forbidden", []))[:12],
    )
    async with database_service.session() as session:
        saved = await nft_visual_template_service.create(session, user_id, payload)
    return _tool_result(
        "save_visual_template",
        "completed",
        f"已将当前作品方向另存为视觉模板「{saved.name}」。",
        saved_template=saved.model_dump(),
    )


@tool
async def generate_nft_image(runtime: ToolRuntime) -> str:
    """Generate a temporary NFT image preview when story state or user intent warrants it."""

    state = runtime.state
    template = state.get("template") or {}
    current_draft = state.get("draft") or {}
    story = str(state.get("story_summary") or "").strip()
    if not template or not current_draft or len(story) < 2:
        return _tool_result(
            "generate_nft_image",
            "degraded",
            "当前作品信息还不完整，暂时无法生成图片。",
        )
    visual_style = str(state.get("visual_style") or "cinematic")
    fallback_style_prompt = next(iter(STYLE_PROMPTS.values()), "premium fan collectible")
    style_prompt = STYLE_PROMPTS.get(visual_style, fallback_style_prompt)
    request = NftDraftRequest(
        theme=str(template.get("name") or "粉丝收藏品"),
        story=story if len(story) >= 10 else f"{story}。请围绕这段真实粉丝记忆创作。",
        visual_style=(
            f"{template.get('prompt', '')}, {style_prompt}. "
            "The supplied reference image controls the recognizable visual identity. Preserve its recurring subjects, "
            "motif repetition, composition density, hand-drawn or graphic line language, and palette relationships. "
            "Do not reinterpret it as an unrelated solitary icon, animal, statue, guardian, or landscape. "
            "CURRENT APPROVED ART DIRECTION, follow this as the source of truth: "
            f"{current_draft.get('image_prompt', '')}"
        )[:2500],
        template_prompt=str(template.get("prompt") or "")[:2000] or None,
        selected_style_prompt=style_prompt[:2000],
        preferred_name=str(current_draft.get("name") or "") or None,
        reference_notes=(
            "故事状态已经成熟或用户已明确要求生成。严格实现当前作品状态，"
            "参考图是视觉主体的第一优先级，必须保留可识别的主体族群、重复图案、构图密度、线条语言和配色关系；"
            "保留主视觉、构图层级、材质、色彩、光线和粉丝收藏品形态；"
            "不要改成无关场景，不要加入 Logo、水印、可读文字或未经授权的真实人物肖像。"
        )[:500],
        reference_image_urls=list(state.get("reference_image_urls", []))[:6],
        iteration_image_url=state.get("last_image_url"),
        generate_image=True,
    )
    generated = await nft_creation_agent.create_draft(request)
    if not generated.image_data_url:
        return _tool_result(
            "generate_nft_image",
            "degraded",
            generated.image_error or "图片生成暂不可用。",
            draft=generated.model_dump(),
        )
    return _tool_result(
        "generate_nft_image",
        "completed",
        "已按当前作品状态生成临时预览图；发布时会直接上传 Pinata。",
        draft=generated.model_dump(),
        image_url=generated.image_data_url,
    )


NFT_VISUAL_TOOLS = (select_visual_template, save_visual_template)
NFT_IMAGE_TOOLS = (generate_nft_image,)
