"""Stateful LangGraph conversation Agent for the NFT creation studio.

The graph owns conversation history and story discovery. Artifact generation and
publishing stay behind explicit tools/services so a chat turn can never mint an NFT.
"""

import json
import operator
from hashlib import sha256
from typing import Annotated, Any, TypedDict
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from app.agents.nft_creation import NftCreationAgent, nft_creation_agent
from app.agents.nft_visual_templates import (
    NFT_STUDIO_SYSTEM_PROMPT,
    NFT_STUDIO_USER_PROMPT_TEMPLATE,
    NFT_TEMPLATE_TOOL_SYSTEM_PROMPT,
    NFT_TEMPLATE_TOOL_USER_PROMPT_TEMPLATE,
    STYLE_PROMPTS,
)
from app.agents.nft_visual_tools import NFT_IMAGE_TOOLS, NFT_VISUAL_TOOLS
from app.core.langgraph.checkpointer import checkpoint_manager
from app.core.logging import logger
from app.schemas.nft_agent import (
    NftAgentChatRequest,
    NftAgentChatResponse,
    NftAgentToolEvent,
    NftDraftRequest,
    NftDraftResponse,
    NftVisualTemplate,
)
from app.services.llm import LLMService, llm_service
from app.services.llm.service import LLMUnavailable


class NftConversationAnalysis(BaseModel):
    assistant_message: str = Field(min_length=2, max_length=500)
    story_summary: str = Field(min_length=2, max_length=1200)
    missing_fields: list[str] = Field(default_factory=list, max_length=4)
    ready_for_generation: bool = False
    visual_change_detected: bool = False
    visual_change_reason: str = Field(default="", max_length=300)
    should_offer_image_generation: bool = False
    should_generate_image: bool = False


class NftStudioState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    user_id: str
    template_id: str
    visual_style: str
    template: dict[str, Any]
    available_templates: list[dict[str, Any]]
    assistant_message: str
    story_summary: str
    missing_fields: list[str]
    ready_for_generation: bool
    turn_count: int
    draft: dict[str, Any] | None
    reference_image_urls: list[str]
    last_image_url: str | None
    last_generated_signature: str
    last_generated_template_id: str
    last_generated_style: str
    last_generated_reference_urls: list[str]
    visual_signature: str
    visual_change_detected: bool
    visual_change_reason: str
    image_generation_recommended: bool
    should_generate_image: bool
    explicit_image_request: bool
    image_generated: bool
    saved_template: dict[str, Any] | None
    tool_context: str
    tool_events: Annotated[list[dict[str, str]], operator.add]


def _human_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    return [message for message in messages if isinstance(message, HumanMessage)]


def _latest_human_message(state: NftStudioState) -> str:
    messages = _human_messages(state.get("messages", []))
    return str(messages[-1].content).strip() if messages else ""


def _wants_select_template(message: str) -> bool:
    normalized = message.replace(" ", "").lower()
    return "模板" in normalized and any(
        trigger in normalized
        for trigger in ("推荐", "选择", "帮我选", "换个", "换一", "适合什么", "用什么")
    )


def _wants_save_template(message: str) -> bool:
    normalized = message.replace(" ", "").lower()
    return "模板" in normalized and any(
        trigger in normalized for trigger in ("保存", "另存", "存成", "创建", "做成")
    )


def _wants_generate_image(message: str) -> bool:
    normalized = "".join(message.lower().split())
    if any(
        command in normalized
        for command in ("不要生成", "别生成", "暂不生成", "先不生成", "不要生图", "别生图", "不生成图片")
    ):
        return False
    direct_commands = (
        "生成图片",
        "生成一张图片",
        "立即生成",
        "马上生成",
        "现在生成",
        "直接生成",
        "开始生成",
        "确认生成",
        "先生成",
        "先出图",
        "出一张图",
        "出张图",
        "做一张预览",
        "生成预览",
        "立即生图",
        "马上生图",
        "现在生图",
        "现在就生图",
        "直接生图",
        "重画",
        "重新画",
    )
    if any(command in normalized for command in direct_commands):
        return True
    return any(term in normalized for term in ("图片", "图像", "画面", "新图", "生图", "预览图")) and any(
        term in normalized for term in ("生成", "确认", "开始", "更新", "重画", "重做", "重新", "来一张", "做一张")
    )


def _has_template_tool_intent(message: str) -> bool:
    return _wants_select_template(message) or _wants_save_template(message)


def _fallback_tool_calls(state: NftStudioState) -> AIMessage:
    message = _latest_human_message(state)
    calls: list[dict[str, Any]] = []
    if _wants_select_template(message):
        catalog = state.get("available_templates", [])
        selected = next(
            (
                item
                for item in catalog
                if any(keyword in message for keyword in (str(item.get("name", "")), str(item.get("category", ""))))
            ),
            catalog[0] if catalog else None,
        )
        if selected:
            calls.append(
                {
                    "name": "select_visual_template",
                    "args": {"template_id": selected["id"], "reason": "与当前故事和收藏品方向最匹配"},
                    "id": f"select-{uuid4().hex[:10]}",
                    "type": "tool_call",
                }
            )
    if _wants_save_template(message):
        draft = state.get("draft") or {}
        template = state.get("template") or {}
        calls.append(
            {
                "name": "save_visual_template",
                "args": {
                    "name": f"{str(draft.get('name') or template.get('name') or '我的作品')[:70]}模板",
                    "category": str(template.get("category") or "粉丝周边")[:40],
                    "description": str(state.get("story_summary") or template.get("description") or "个人 NFT 视觉方向")[:500],
                },
                "id": f"save-{uuid4().hex[:10]}",
                "type": "tool_call",
            }
        )
    return AIMessage(content="", tool_calls=calls)


def _fallback_analysis(state: NftStudioState) -> NftConversationAnalysis:
    human_messages = _human_messages(state.get("messages", []))
    story_messages = [
        str(message.content).strip()
        for message in human_messages
        if str(message.content).strip()
        and not _wants_save_template(str(message.content))
        and not _wants_generate_image(str(message.content))
        and not _wants_select_template(str(message.content))
    ]
    story = " ".join(story_messages)
    if len(human_messages) <= 1:
        return NftConversationAnalysis(
            assistant_message="我先整理出了一版创作方向。你可以继续补充喜欢的性格、歌曲带来的画面、生活中的陪伴感，或想保留的象征物。",
            story_summary=story or "一段正在形成的真实粉丝记忆",
            missing_fields=["核心画面", "情绪落点"],
            ready_for_generation=False,
            visual_change_detected=True,
            visual_change_reason="建立了第一版可视化故事方向",
            should_offer_image_generation=True,
            should_generate_image=False,
        )
    if len(story) < 45:
        story_summary = story or state.get("story_summary") or "一段正在形成的粉丝创作灵感"
        return NftConversationAnalysis(
            assistant_message="再告诉我它最接近哪一种情绪，以及你希望观众第一眼看到什么；不需要有现场经历，也可以来自性格或歌曲带来的想象。",
            story_summary=str(story_summary)[:1200],
            missing_fields=["情绪落点"],
            ready_for_generation=False,
            visual_change_detected=not (
                _wants_save_template(_latest_human_message(state)) or _wants_generate_image(_latest_human_message(state))
            ),
            visual_change_reason="故事中的可视化信息发生变化",
            should_offer_image_generation=True,
            should_generate_image=False,
        )
    return NftConversationAnalysis(
        assistant_message="故事线已经完整。我整理好了 NFT 名称、作品描述与视觉提示词，你可以继续补充，或进入图片生成。",
        story_summary=(story or "一段正在形成的真实粉丝记忆")[:1200],
        missing_fields=[],
        ready_for_generation=True,
        visual_change_detected=not (
            _wants_save_template(_latest_human_message(state)) or _wants_generate_image(_latest_human_message(state))
        ),
        visual_change_reason="故事、画面或视觉方向发生变化",
        should_offer_image_generation=True,
        should_generate_image=True,
    )


def _visual_signature(state: NftStudioState, draft: NftDraftResponse) -> str:
    payload = {
        "template_id": (state.get("template") or {}).get("id"),
        "visual_style": state.get("visual_style"),
        "reference_image_urls": sorted(state.get("reference_image_urls", [])),
        "story_summary": state.get("story_summary", ""),
        "image_prompt": draft.image_prompt,
    }
    return sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _required_template(state: NftStudioState) -> dict[str, Any]:
    template = state.get("template")
    if not template:
        raise ValueError("Visual template is required and must be loaded from the database")
    return template


def build_nft_studio_graph(
    model_service: LLMService,
    draft_agent: NftCreationAgent,
    checkpointer: Any,
) -> CompiledStateGraph:
    def load_template(state: NftStudioState) -> dict[str, Any]:
        template = _required_template(state)
        return {
            "template": template,
            "reference_image_urls": list(
                dict.fromkeys([*template.get("reference_image_urls", []), *state.get("reference_image_urls", [])])
            )[:6],
            "tool_events": [{"tool": "load_visual_template", "status": "completed", "summary": template["name"]}],
        }

    async def plan_template_tools(state: NftStudioState) -> dict[str, Any]:
        latest_message = _latest_human_message(state)
        if not _has_template_tool_intent(latest_message):
            return {}
        human_messages = _human_messages(state.get("messages", []))
        transcript = "\n".join(f"用户：{message.content}" for message in human_messages[-10:])
        template = _required_template(state)
        catalog = state.get("available_templates", [])
        catalog_text = "\n".join(
            f"- {item['id']} | {item['name']} | {item['category']} | {item['description']}" for item in catalog
        )
        try:
            decision = await model_service.call_with_tools(
                [
                    SystemMessage(content=NFT_TEMPLATE_TOOL_SYSTEM_PROMPT),
                    HumanMessage(
                        content=NFT_TEMPLATE_TOOL_USER_PROMPT_TEMPLATE.format(
                            current_template_name=template["name"],
                            current_template_id=template["id"],
                            story_summary=state.get("story_summary", "尚未形成故事摘要"),
                            draft_name=(state.get("draft") or {}).get("name", "尚未生成"),
                            template_catalog=catalog_text or "暂无可用模板",
                            transcript=transcript,
                            latest_message=latest_message,
                        )
                    ),
                ],
                NFT_VISUAL_TOOLS,
            )
        except LLMUnavailable:
            decision = _fallback_tool_calls(state)
        return {"messages": [decision]}

    def route_template_tools(state: NftStudioState) -> str:
        messages = state.get("messages", [])
        latest = messages[-1] if messages else None
        return "template_tools" if isinstance(latest, AIMessage) and latest.tool_calls else "interview_story"

    def apply_template_tool_results(state: NftStudioState) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        events: list[dict[str, str]] = []
        summaries: list[str] = []
        for message in reversed(state.get("messages", [])):
            if not isinstance(message, ToolMessage):
                break
            try:
                result = json.loads(str(message.content))
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
            action = str(result.get("action") or message.name or "visual_template_tool")
            status = "completed" if result.get("status") == "completed" else "degraded"
            summary = str(result.get("summary") or "视觉模板工具已执行。")
            events.append({"tool": action, "status": status, "summary": summary})
            summaries.append(summary)
            if result.get("template"):
                template = NftVisualTemplate.model_validate(result["template"])
                updates.update(
                    {
                        "template": template.model_dump(),
                        "template_id": template.id,
                        "reference_image_urls": template.reference_image_urls,
                    }
                )
            if result.get("saved_template"):
                updates["saved_template"] = NftVisualTemplate.model_validate(result["saved_template"]).model_dump()
        if events:
            updates["tool_events"] = list(reversed(events))
            updates["tool_context"] = " ".join(reversed(summaries))
        return updates

    async def interview_story(state: NftStudioState) -> dict[str, Any]:
        messages = state.get("messages", [])
        fallback = _fallback_analysis(state)
        analysis = fallback
        if model_service.available:
            transcript = "\n".join(f"用户：{message.content}" for message in _human_messages(messages)[-10:])
            template = _required_template(state)
            try:
                analysis = await model_service.call_structured(
                    [
                        SystemMessage(content=NFT_STUDIO_SYSTEM_PROMPT),
                        HumanMessage(
                            content=NFT_STUDIO_USER_PROMPT_TEMPLATE.format(
                                template_name=template["name"],
                                template_description=template["description"],
                                template_prompt=template["prompt"],
                                visual_style=state.get("visual_style", "cinematic"),
                                elements="、".join(template.get("elements", [])) or "由故事决定",
                                forbidden="、".join(template.get("forbidden", [])) or "Logo、水印、可读文字",
                                reference_count=len(state.get("reference_image_urls", [])),
                                last_generated_template_id=state.get("last_generated_template_id") or "尚未生成",
                                last_generated_style=state.get("last_generated_style") or "尚未生成",
                                last_generated_reference_count=len(state.get("last_generated_reference_urls", [])),
                                transcript=transcript,
                            )
                        ),
                    ],
                    NftConversationAnalysis,
                )
            except (LLMUnavailable, ValueError, TypeError):
                logger.exception("nft_studio_interview_fallback")
        human_count = len(_human_messages(messages))
        tool_context = state.get("tool_context", "").strip()
        assistant_message = f"{tool_context} {analysis.assistant_message}".strip() if tool_context else analysis.assistant_message
        return {
            "assistant_message": assistant_message,
            "story_summary": analysis.story_summary,
            "missing_fields": analysis.missing_fields,
            "ready_for_generation": analysis.ready_for_generation,
            "visual_change_detected": analysis.visual_change_detected,
            "visual_change_reason": analysis.visual_change_reason,
            "should_generate_image": analysis.should_generate_image,
            "turn_count": human_count,
        }

    async def compose_draft(state: NftStudioState) -> dict[str, Any]:
        template = _required_template(state)
        fallback_style_prompt = next(iter(STYLE_PROMPTS.values()), "premium fan collectible")
        style_prompt = STYLE_PROMPTS.get(state.get("visual_style", "cinematic"), fallback_style_prompt)
        story = state.get("story_summary", "").strip()
        if len(story) < 10:
            story = f"{story}。请围绕这段真实粉丝记忆继续创作。"
        request = NftDraftRequest(
            theme=template["name"],
            story=story,
            visual_style=f"{template['prompt']}, {style_prompt}",
            template_prompt=template["prompt"],
            selected_style_prompt=style_prompt,
            preferred_name=(state.get("draft") or {}).get("name"),
            reference_notes=(
                f"本轮必须持续优化上一版。参考元素：{', '.join(template['elements'])}。"
                f"避免：{', '.join(template['forbidden'])}。作品应具备明确的粉丝周边或收藏品形态。"
            ),
            reference_image_urls=state.get("reference_image_urls", []),
            iteration_image_url=state.get("last_image_url"),
            generate_image=False,
        )
        draft = await draft_agent.create_draft(request)
        image_url = state.get("last_image_url")
        draft = draft.model_copy(update={"image_data_url": image_url})
        return {
            "draft": draft.model_dump(),
            "last_image_url": image_url,
            "visual_signature": _visual_signature(state, draft),
            "tool_events": [
                {"tool": "compose_nft_artifact", "status": "completed", "summary": "名称、描述与艺术提示词已优化"}
            ],
        }

    def plan_image_tool(state: NftStudioState) -> dict[str, Any]:
        signature_changed = state.get("visual_signature") != state.get("last_generated_signature")
        explicit_request = bool(state.get("explicit_image_request")) or _wants_generate_image(
            _latest_human_message(state)
        )
        second_turn_preview = bool(state.get("turn_count", 0) >= 2 and not state.get("last_image_url"))
        automatic_generation = bool(
            state.get("ready_for_generation")
            and state.get("should_generate_image")
            and state.get("visual_change_detected")
            and signature_changed
        )
        if not explicit_request and not second_turn_preview and not automatic_generation:
            return {}
        return {
            "messages": [
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "generate_nft_image",
                            "args": {},
                            "id": f"image-{uuid4().hex[:10]}",
                            "type": "tool_call",
                        }
                    ],
                )
            ]
        }

    def route_image_tool(state: NftStudioState) -> str:
        messages = state.get("messages", [])
        latest = messages[-1] if messages else None
        return "image_tools" if isinstance(latest, AIMessage) and latest.tool_calls else "finalize_image_offer"

    def finalize_image_offer(state: NftStudioState) -> dict[str, Any]:
        template_id = str((state.get("template") or {}).get("id") or "")
        structural_change = bool(
            state.get("last_generated_signature")
            and (
                template_id != state.get("last_generated_template_id")
                or state.get("visual_style") != state.get("last_generated_style")
                or sorted(state.get("reference_image_urls", []))
                != sorted(state.get("last_generated_reference_urls", []))
            )
        )
        signature_changed = state.get("visual_signature") != state.get("last_generated_signature")
        recommended = bool(signature_changed and (state.get("visual_change_detected") or structural_change))
        reason = state.get("visual_change_reason", "") or (
            "视觉模板、风格或参考图发生变化" if structural_change else "当前画面方向值得更新"
        )
        assistant_message = state.get("assistant_message", "")
        if recommended and "生成" not in assistant_message[-40:]:
            assistant_message = f"{assistant_message}\n\n画面方向已经更新；故事更完整后我会直接生成新版本，你也可以明确说“生成图片”。"
        return {
            "assistant_message": assistant_message,
            "image_generation_recommended": recommended,
            "visual_change_reason": reason if recommended else "",
            "image_generated": False,
            "tool_events": [
                {
                    "tool": "evaluate_image_generation",
                    "status": "completed",
                    "summary": f"建议生成新图：{reason}" if recommended else "本轮无需重新生成图片",
                }
            ],
        }

    def apply_image_tool_result(state: NftStudioState) -> dict[str, Any]:
        latest = next((message for message in reversed(state.get("messages", [])) if isinstance(message, ToolMessage)), None)
        if latest is None:
            return finalize_image_offer(state)
        try:
            result = json.loads(str(latest.content))
        except (TypeError, ValueError, json.JSONDecodeError):
            raw_error = str(latest.content).strip()
            summary = raw_error.removeprefix("Error:").split("\n", 1)[0].strip() or "图片生成工具执行失败"
            logger.error("nft_image_tool_failed", error=summary)
            return {
                "image_generated": False,
                "image_generation_recommended": True,
                "visual_change_reason": summary,
                "assistant_message": f"{state.get('assistant_message', '')}\n\n图片生成失败：{summary}".strip(),
                "tool_events": [
                    {
                        "tool": "generate_nft_image",
                        "status": "degraded",
                        "summary": summary,
                    }
                ],
            }
        completed = bool(result.get("image_url"))
        tool_status = "completed" if result.get("status") == "completed" else "degraded"
        updates: dict[str, Any] = {
            "image_generated": completed,
            "image_generation_recommended": not completed,
            "visual_change_reason": "" if completed else str(result.get("summary") or "图片生成暂未完成"),
            "assistant_message": f"{state.get('assistant_message', '')}\n\n{result.get('summary', '')}".strip(),
            "tool_events": [
                {
                    "tool": "generate_nft_image",
                    "status": tool_status,
                    "summary": str(result.get("summary") or "图片生成工具执行完成"),
                }
            ],
        }
        if result.get("draft"):
            updates["draft"] = NftDraftResponse.model_validate(result["draft"]).model_dump()
        if completed:
            updates.update(
                {
                    "last_image_url": result["image_url"],
                    "last_generated_signature": state.get("visual_signature", ""),
                    "last_generated_template_id": str((state.get("template") or {}).get("id") or ""),
                    "last_generated_style": state.get("visual_style", ""),
                    "last_generated_reference_urls": state.get("reference_image_urls", []),
                }
            )
        return updates

    workflow = StateGraph(NftStudioState)
    workflow.add_node("load_visual_template", load_template)
    workflow.add_node("plan_template_tools", plan_template_tools)
    workflow.add_node("template_tools", ToolNode(NFT_VISUAL_TOOLS, handle_tool_errors=True))
    workflow.add_node("apply_template_tool_results", apply_template_tool_results)
    workflow.add_node("interview_story", interview_story)
    workflow.add_node("compose_nft_brief", compose_draft)
    workflow.add_node("plan_image_tool", plan_image_tool)
    workflow.add_node("image_tools", ToolNode(NFT_IMAGE_TOOLS, handle_tool_errors=True))
    workflow.add_node("finalize_image_offer", finalize_image_offer)
    workflow.add_node("apply_image_tool_result", apply_image_tool_result)
    workflow.add_edge(START, "load_visual_template")
    workflow.add_edge("load_visual_template", "plan_template_tools")
    workflow.add_conditional_edges(
        "plan_template_tools",
        route_template_tools,
        {"template_tools": "template_tools", "interview_story": "interview_story"},
    )
    workflow.add_edge("template_tools", "apply_template_tool_results")
    workflow.add_edge("apply_template_tool_results", "interview_story")
    workflow.add_edge("interview_story", "compose_nft_brief")
    workflow.add_edge("compose_nft_brief", "plan_image_tool")
    workflow.add_conditional_edges(
        "plan_image_tool",
        route_image_tool,
        {"image_tools": "image_tools", "finalize_image_offer": "finalize_image_offer"},
    )
    workflow.add_edge("image_tools", "apply_image_tool_result")
    workflow.add_edge("apply_image_tool_result", END)
    workflow.add_edge("finalize_image_offer", END)
    return workflow.compile(checkpointer=checkpointer)


class NftStudioAgent:
    def __init__(self, model_service: LLMService = llm_service, draft_agent: NftCreationAgent = nft_creation_agent) -> None:
        self._model_service = model_service
        self._draft_agent = draft_agent
        self._graph = build_nft_studio_graph(model_service, draft_agent, InMemorySaver())

    async def initialize(self) -> None:
        checkpointer = await checkpoint_manager.initialize()
        self._graph = build_nft_studio_graph(
            self._model_service,
            self._draft_agent,
            checkpointer or InMemorySaver(),
        )
        logger.info("nft_studio_agent_initialized", checkpointing="postgres" if checkpointer else "memory")

    async def chat(
        self,
        user_id: str,
        request: NftAgentChatRequest,
        template: NftVisualTemplate,
        available_templates: list[NftVisualTemplate] | None = None,
    ) -> NftAgentChatResponse:
        conversation_id = request.conversation_id or uuid4().hex
        config: RunnableConfig = {"configurable": {"thread_id": f"nft-studio:{user_id}:{conversation_id}"}}
        resolved_available_templates = available_templates or [template]
        result = await self._graph.ainvoke(
            {
                "messages": [HumanMessage(content=request.message.strip())],
                "user_id": user_id,
                "template_id": request.template_id,
                "template": template.model_dump(),
                "available_templates": [item.model_dump() for item in resolved_available_templates],
                "visual_style": request.visual_style,
                "reference_image_urls": request.reference_image_urls,
                "saved_template": None,
                "tool_context": "",
                "image_generation_recommended": False,
                "explicit_image_request": _wants_generate_image(request.message),
                "image_generated": False,
                "tool_events": [],
            },
            config=config,
        )
        resolved_template = NftVisualTemplate.model_validate(result.get("template"))
        draft = NftDraftResponse.model_validate(result["draft"]) if result.get("draft") else None
        events = [NftAgentToolEvent.model_validate(item) for item in result.get("tool_events", [])[-6:]]
        saved_template = (
            NftVisualTemplate.model_validate(result["saved_template"]) if result.get("saved_template") else None
        )
        return NftAgentChatResponse(
            conversation_id=conversation_id,
            assistant_message=result["assistant_message"],
            story_summary=result.get("story_summary", ""),
            missing_fields=result.get("missing_fields", []),
            ready_for_generation=bool(result.get("ready_for_generation")),
            turn_count=int(result.get("turn_count", 1)),
            template=resolved_template,
            draft=draft,
            saved_template=saved_template,
            image_generation_recommended=bool(result.get("image_generation_recommended")),
            image_generation_reason=result.get("visual_change_reason", ""),
            image_generated=bool(result.get("image_generated")),
            tool_events=events,
        )


nft_studio_agent = NftStudioAgent()
