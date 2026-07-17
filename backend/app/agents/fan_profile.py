"""LangGraph workflow for deterministic scoring and optional LLM enrichment."""

from typing import Any, Required, TypedDict
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.core.config import settings
from app.core.langgraph.checkpointer import checkpoint_manager
from app.core.logging import logger
from app.core.metrics import fan_profile_runs_total
from app.schemas.fan_profile import (
    BadgeDraft,
    FanProfileAnalysis,
    FanProfileNarrative,
    FanProfileRequest,
    FanProfileScores,
    FanType,
)
from app.services.llm import LLMService, llm_service
from app.services.llm.service import LLMUnavailable


class FanProfileState(TypedDict, total=False):
    wallet_address: Required[str]
    community_id: Required[str]
    points: Required[int]
    completed_tasks: Required[int]
    active_days: Required[int]
    referrals: Required[int]
    onchain_actions: Required[int]
    scores: Required[dict[str, int]]
    fan_type: Required[FanType]
    summary: Required[str]
    analysis_source: Required[str]
    badge_eligible: Required[bool]
    badge_draft: Required[dict[str, str] | None]


def calculate_scores(state: FanProfileState) -> dict[str, Any]:
    activity = min(state.get("completed_tasks", 0) * 8 + state.get("active_days", 0) * 2, 100)
    loyalty = min(state.get("active_days", 0) * 5 + state.get("points", 0) // 20, 100)
    influence = min(state.get("referrals", 0) * 20 + state.get("onchain_actions", 0) * 3, 100)
    contribution = min(state.get("points", 0) // 10 + state.get("completed_tasks", 0) * 5, 100)
    total = round(activity * 0.3 + loyalty * 0.3 + influence * 0.15 + contribution * 0.25)
    return {
        "scores": {
            "activity": activity,
            "loyalty": loyalty,
            "influence": influence,
            "contribution": contribution,
            "total": total,
        },
        "badge_eligible": state.get("points", 0) >= settings.badge_draft_min_points,
    }


def classify_fan(state: FanProfileState) -> dict[str, FanType]:
    score = state["scores"]["total"]
    if score >= 80:
        fan_type: FanType = "core_contributor"
    elif state.get("referrals", 0) >= 3:
        fan_type = "advocate"
    elif state.get("active_days", 0) >= 10:
        fan_type = "loyal_fan"
    else:
        fan_type = "emerging_fan"
    return {"fan_type": fan_type}


def _rule_summary(state: FanProfileState) -> str:
    return (
        f"This wallet is classified as {state['fan_type']} with a total score of "
        f"{state['scores']['total']}/100 based on verified Fanora activity."
    )


def _rule_badge_draft(state: FanProfileState) -> dict[str, str] | None:
    if not state.get("badge_eligible"):
        return None
    return {
        "name": f"{state['fan_type'].replace('_', ' ').title()} Badge",
        "description": "Proof of Fandom badge generated from verified Fanora points and activity.",
        "level": state["fan_type"],
    }


def build_fan_profile_graph(
    model_service: LLMService = llm_service,
    checkpointer: Any | None = None,
) -> CompiledStateGraph:
    async def enrich_with_llm(state: FanProfileState) -> dict[str, Any]:
        fallback = {
            "summary": _rule_summary(state),
            "analysis_source": "rules",
            "badge_draft": _rule_badge_draft(state),
        }
        if not model_service.available:
            return fallback

        messages = [
            SystemMessage(
                content=(
                    "You analyze verified Fanora fan activity. Return a concise classification explanation. "
                    "Do not change scores, grant rewards, or claim that a badge was minted."
                )
            ),
            HumanMessage(
                content=(
                    f"Community: {state['community_id']}\nPoints: {state['points']}\n"
                    f"Completed tasks: {state['completed_tasks']}\nActive days: {state['active_days']}\n"
                    f"Referrals: {state['referrals']}\nOnchain actions: {state['onchain_actions']}\n"
                    f"Verified scores: {state['scores']}\nRule classification: {state['fan_type']}\n"
                    f"Badge draft eligible: {state['badge_eligible']}"
                )
            ),
        ]
        try:
            narrative = await model_service.call_structured(messages, FanProfileNarrative)
            draft = None
            if state.get("badge_eligible"):
                rule_draft = _rule_badge_draft(state)
                if rule_draft is None:
                    raise ValueError("badge draft rules returned no draft for an eligible profile")
                draft = {
                    "name": narrative.badge_name or rule_draft["name"],
                    "description": narrative.badge_description or rule_draft["description"],
                    "level": narrative.fan_type,
                }
            return {
                "fan_type": narrative.fan_type,
                "summary": narrative.summary,
                "analysis_source": "llm",
                "badge_draft": draft,
            }
        except (LLMUnavailable, KeyError, TypeError):
            logger.exception("fan_profile_llm_fallback")
            return fallback

    workflow = StateGraph(FanProfileState)
    workflow.add_node("calculate_scores", calculate_scores)
    workflow.add_node("classify_fan", classify_fan)
    workflow.add_node("enrich_with_llm", enrich_with_llm)
    workflow.add_edge(START, "calculate_scores")
    workflow.add_edge("calculate_scores", "classify_fan")
    workflow.add_edge("classify_fan", "enrich_with_llm")
    workflow.add_edge("enrich_with_llm", END)
    return workflow.compile(checkpointer=checkpointer)


class FanProfileAgent:
    """Deep module exposing one analysis interface to the rest of Fanora."""

    def __init__(self, model_service: LLMService = llm_service) -> None:
        self.model_service = model_service
        self._graph: CompiledStateGraph | None = None

    async def initialize(self) -> None:
        if self._graph is None:
            checkpointer = await checkpoint_manager.initialize()
            self._graph = build_fan_profile_graph(self.model_service, checkpointer)
            logger.info("fan_profile_agent_initialized", checkpointing=checkpointer is not None)

    async def analyze(self, request: FanProfileRequest) -> FanProfileAnalysis:
        await self.initialize()
        graph = self._graph
        if graph is None:
            raise RuntimeError("fan profile graph failed to initialize")
        run_id = str(uuid4())
        config: RunnableConfig = {"configurable": {"thread_id": run_id}}
        try:
            result = await graph.ainvoke(request.model_dump(), config=config)
            source = result.get("analysis_source", "rules")
            fan_profile_runs_total.labels(source, "success").inc()
            return FanProfileAnalysis(
                run_id=run_id,
                wallet_address=request.wallet_address,
                community_id=request.community_id,
                scores=FanProfileScores(**result["scores"]),
                fan_type=result["fan_type"],
                summary=result["summary"],
                analysis_source=source,
                badge_eligible=result["badge_eligible"],
                badge_draft=BadgeDraft(**result["badge_draft"]) if result.get("badge_draft") else None,
            )
        except Exception:
            fan_profile_runs_total.labels("unknown", "error").inc()
            raise


fan_profile_agent = FanProfileAgent()
