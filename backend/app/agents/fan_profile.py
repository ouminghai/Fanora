"""Complete LangGraph fan-profile workflow: prepare, score, recommend, and persist."""

from collections.abc import Awaitable, Callable
from typing import Any, Required, TypedDict
from uuid import uuid4

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from app.core.config import settings
from app.core.langgraph.checkpointer import checkpoint_manager
from app.core.logging import logger
from app.core.metrics import fan_profile_runs_total
from app.models.base import utc_now
from app.models.community import (
    CommunityPost,
    CommunityReply,
    DailyCheckIn,
    FanTask,
    TaskContentReview,
    TaskParticipation,
)
from app.models.fan_profile import FanProfileRun
from app.models.nft import ChainOperation, CollectibleOwnership
from app.models.user import CommunityMember, UserProfile
from app.schemas.fan_profile import (
    BadgeDraft,
    FanProfileAnalysis,
    FanProfileNarrative,
    FanProfileRequest,
    FanProfileScores,
    FanType,
    TaskRecommendation,
)
from app.services.auth import as_utc
from app.services.llm import LLMService, llm_service
from app.services.llm.service import LLMUnavailable


class FanProfileState(TypedDict, total=False):
    run_id: Required[str]
    user_id: str | None
    wallet_address: Required[str]
    fan_token_balance: Required[int]
    completed_tasks: Required[int]
    active_days: Required[int]
    referrals: Required[int]
    onchain_actions: Required[int]
    chain_summary: Required[dict[str, Any]]
    risk_signals: Required[list[str]]
    scores: Required[dict[str, int]]
    fan_type: Required[FanType]
    labels: Required[list[str]]
    risk_level: Required[str]
    summary: Required[str]
    analysis_source: Required[str]
    badge_eligible: Required[bool]
    badge_draft: Required[dict[str, Any] | None]
    task_candidates: Required[list[dict[str, Any]]]
    recommended_tasks: Required[list[dict[str, Any]]]


PrepareData = Callable[[FanProfileState], Awaitable[dict[str, Any]]]
PersistResult = Callable[[FanProfileState], Awaitable[dict[str, Any] | None]]


def prepare_supplied_data(state: FanProfileState) -> dict[str, Any]:
    """Make data preparation an explicit graph step for direct/internal analyses."""

    return {
        "fan_token_balance": max(int(state.get("fan_token_balance", 0)), 0),
        "completed_tasks": max(int(state.get("completed_tasks", 0)), 0),
        "active_days": max(int(state.get("active_days", 0)), 0),
        "referrals": max(int(state.get("referrals", 0)), 0),
        "onchain_actions": max(int(state.get("onchain_actions", 0)), 0),
        "chain_summary": state.get("chain_summary", {}),
        "risk_signals": state.get("risk_signals", []),
        "task_candidates": state.get("task_candidates", []),
    }


def calculate_scores(state: FanProfileState) -> dict[str, Any]:
    activity = min(state.get("completed_tasks", 0) * 8 + state.get("active_days", 0) * 2, 100)
    loyalty = min(state.get("active_days", 0) * 5 + state.get("fan_token_balance", 0) // 20, 100)
    influence = min(state.get("referrals", 0) * 20 + state.get("onchain_actions", 0) * 3, 100)
    contribution = min(state.get("fan_token_balance", 0) // 10 + state.get("completed_tasks", 0) * 5, 100)
    total = round(activity * 0.3 + loyalty * 0.3 + influence * 0.15 + contribution * 0.25)
    return {
        "scores": {
            "activity": activity,
            "loyalty": loyalty,
            "influence": influence,
            "contribution": contribution,
            "total": total,
        },
        "badge_eligible": state.get("fan_token_balance", 0) >= settings.badge_draft_min_tokens,
    }


def classify_fan(state: FanProfileState) -> dict[str, FanType]:
    score = state["scores"]["total"]
    if score >= 80:
        fan_type: FanType = "high_value_contributor"
    elif state.get("referrals", 0) >= 3:
        fan_type = "advocate"
    elif state.get("active_days", 0) >= 30:
        fan_type = "loyal_fan"
    elif state.get("active_days", 0) >= 10:
        fan_type = "active_fan"
    elif state.get("chain_summary", {}).get("early_supporter") is True:
        fan_type = "early_supporter"
    else:
        fan_type = "emerging_fan"
    labels: list[str] = [fan_type]
    if state.get("active_days", 0) >= 30 and "loyal_fan" not in labels:
        labels.append("loyal_fan")
    if state.get("referrals", 0) >= 3 and "advocate" not in labels:
        labels.append("advocate")
    if state.get("completed_tasks", 0) >= 10 and "active_fan" not in labels:
        labels.append("active_fan")
    if state.get("chain_summary", {}).get("early_supporter") is True and "early_supporter" not in labels:
        labels.append("early_supporter")
    risk_count = len(state.get("risk_signals", []))
    risk_level = "high" if risk_count >= 3 else "medium" if risk_count else "low"
    return {"fan_type": fan_type, "labels": labels, "risk_level": risk_level}  # type: ignore[return-value]


def _rule_summary(state: FanProfileState) -> str:
    return (
        f"This wallet is classified as {state['fan_type']} with a total score of "
        f"{state['scores']['total']}/100 based on verified Fanora activity."
    )


def _rule_badge_draft(state: FanProfileState) -> dict[str, Any] | None:
    if not state.get("badge_eligible"):
        return None
    return {
        "name": f"{state['fan_type'].replace('_', ' ').title()} Badge",
        "description": "Proof of Fandom badge draft generated from verified Fanora activity.",
        "level": state["fan_type"],
        "image_prompt": "A premium Fanora digital commemorative badge with musical energy and verifiable fandom symbolism.",
        "suggested_attributes": [
            {"trait_type": "Fan Type", "value": state["fan_type"]},
            {"trait_type": "Score", "value": str(state["scores"]["total"])},
        ],
    }


def recommend_tasks(state: FanProfileState) -> dict[str, Any]:
    preferences = {
        "emerging_fan": ["daily_check_in", "post_reply", "page_action"],
        "active_fan": ["content_publish", "page_action", "post_reply"],
        "loyal_fan": ["page_action", "content_publish", "daily_check_in"],
        "advocate": ["content_publish", "post_reply", "page_action"],
        "early_supporter": ["page_action", "content_publish", "future"],
        "high_value_contributor": ["content_publish", "page_action", "post_reply"],
    }
    preferred_types = preferences.get(state["fan_type"], [])
    ranked: list[tuple[int, dict[str, Any]]] = []
    for candidate in state.get("task_candidates", []):
        task_type = str(candidate.get("task_type", ""))
        type_score = len(preferred_types) - preferred_types.index(task_type) if task_type in preferred_types else 0
        reward_score = min(int(candidate.get("reward_fan_tokens", 0)) // 50, 5)
        ranked.append((type_score * 10 + reward_score, candidate))
    recommendations = []
    for _, candidate in sorted(ranked, key=lambda item: item[0], reverse=True)[:5]:
        task_type = str(candidate.get("task_type", ""))
        if task_type in preferred_types:
            reason = f"适合当前 {state['fan_type']} 画像，可继续积累真实互动与贡献记录。"
        else:
            reason = "任务当前有效且符合参与资格，可补充粉丝画像中的活跃记录。"
        recommendations.append(
            {
                "task_id": candidate["task_id"],
                "title": candidate["title"],
                "reason": reason,
                "reward_fan_tokens": candidate["reward_fan_tokens"],
                "action_url": candidate["action_url"],
            }
        )
    return {"recommended_tasks": recommendations}


def build_fan_profile_graph(
    model_service: LLMService = llm_service,
    checkpointer: Any | None = None,
    prepare_data: PrepareData | None = None,
    persist_result: PersistResult | None = None,
) -> CompiledStateGraph:
    async def prepare(state: FanProfileState) -> dict[str, Any]:
        if prepare_data is None:
            return prepare_supplied_data(state)
        return await prepare_data(state)

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
                    f"Fan Token balance: {state['fan_token_balance']}\n"
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
                    "image_prompt": narrative.image_prompt or rule_draft["image_prompt"],
                    "suggested_attributes": rule_draft["suggested_attributes"],
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

    async def persist(state: FanProfileState) -> dict[str, Any]:
        if persist_result is not None:
            await persist_result(state)
        return {}

    workflow = StateGraph(FanProfileState)
    workflow.add_node("prepare_data", prepare)
    workflow.add_node("calculate_scores", calculate_scores)
    workflow.add_node("classify_fan", classify_fan)
    workflow.add_node("enrich_with_llm", enrich_with_llm)
    workflow.add_node("recommend_tasks", recommend_tasks)
    workflow.add_node("persist_result", persist)
    workflow.add_edge(START, "prepare_data")
    workflow.add_edge("prepare_data", "calculate_scores")
    workflow.add_edge("calculate_scores", "classify_fan")
    workflow.add_edge("classify_fan", "enrich_with_llm")
    workflow.add_edge("enrich_with_llm", "recommend_tasks")
    workflow.add_edge("recommend_tasks", "persist_result")
    workflow.add_edge("persist_result", END)
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

    async def _prepare_user_data(
        self,
        session: AsyncSession,
        user_id: str,
        wallet_address: str,
        _: FanProfileState,
    ) -> dict[str, Any]:
        profile = await session.get(UserProfile, user_id)
        if profile is None:
            raise ValueError("User profile not found")
        completed_tasks = int(
            (
                await session.execute(
                    select(func.count(col(TaskParticipation.id))).where(
                        TaskParticipation.user_id == user_id,
                        TaskParticipation.status == "rewarded",
                    )
                )
            ).scalar_one()
        )
        active_dates = set(
            (await session.execute(select(col(DailyCheckIn.check_in_date)).where(DailyCheckIn.user_id == user_id)))
            .scalars()
            .all()
        )
        for timestamp in (
            (await session.execute(select(CommunityPost.created_at).where(CommunityPost.author_user_id == user_id)))
            .scalars()
            .all()
        ):
            active_dates.add(timestamp.date())
        for timestamp in (
            (await session.execute(select(CommunityReply.created_at).where(CommunityReply.author_user_id == user_id)))
            .scalars()
            .all()
        ):
            active_dates.add(timestamp.date())
        onchain_actions = int(
            (
                await session.execute(
                    select(func.count(col(ChainOperation.id))).where(
                        ChainOperation.user_id == user_id,
                        ChainOperation.status == "CONFIRMED",
                    )
                )
            ).scalar_one()
        )
        collectible_count = int(
            (
                await session.execute(
                    select(func.count(col(CollectibleOwnership.id))).where(
                        CollectibleOwnership.user_id == user_id,
                        CollectibleOwnership.status == "CONFIRMED",
                        CollectibleOwnership.amount > 0,
                    )
                )
            ).scalar_one()
        )
        rejected_reviews = int(
            (
                await session.execute(
                    select(func.count(col(TaskContentReview.id))).where(
                        TaskContentReview.user_id == user_id,
                        TaskContentReview.decision == "rejected",
                    )
                )
            ).scalar_one()
        )
        retryable_chain_operations = int(
            (
                await session.execute(
                    select(func.count(col(ChainOperation.id))).where(
                        ChainOperation.user_id == user_id,
                        col(ChainOperation.status).in_(["FAILED", "RETRYABLE"]),
                    )
                )
            ).scalar_one()
        )
        risk_signals: list[str] = []
        if rejected_reviews >= 3:
            risk_signals.append("repeated_content_rejections")
        if retryable_chain_operations >= 3:
            risk_signals.append("repeated_chain_failures")

        joined = (
            await session.execute(select(CommunityMember.id).where(CommunityMember.user_id == user_id).limit(1))
        ).scalar_one_or_none() is not None
        participation_ids = set(
            (await session.execute(select(TaskParticipation.task_id).where(TaskParticipation.user_id == user_id)))
            .scalars()
            .all()
        )
        now = utc_now()
        task_candidates: list[dict[str, Any]] = []
        if profile.is_official_member and joined:
            tasks = list(
                (
                    await session.execute(
                        select(FanTask)
                        .where(FanTask.status == "published")
                        .order_by(col(FanTask.reward_fan_tokens).desc())
                    )
                )
                .scalars()
                .all()
            )
            for task in tasks:
                if task.id in participation_ids:
                    continue
                if task.start_at and as_utc(task.start_at) > now:
                    continue
                if task.end_at and as_utc(task.end_at) < now:
                    continue
                presentation = task.validation_rule.get("presentation", {})
                action_url = (
                    presentation.get("action_url", "/community/tasks")
                    if isinstance(presentation, dict)
                    else "/community/tasks"
                )
                task_candidates.append(
                    {
                        "task_id": task.id,
                        "title": task.title,
                        "task_type": task.task_type,
                        "reward_fan_tokens": task.reward_fan_tokens,
                        "action_url": action_url,
                    }
                )
        early_supporter = bool(
            profile.official_member_since and (now - as_utc(profile.official_member_since)).days >= 30
        )
        return {
            "wallet_address": wallet_address,
            "fan_token_balance": profile.fan_token_balance,
            "completed_tasks": completed_tasks,
            "active_days": len(active_dates),
            "referrals": 0,
            "onchain_actions": onchain_actions,
            "chain_summary": {
                "confirmed_collectibles": collectible_count,
                "confirmed_operations": onchain_actions,
                "early_supporter": early_supporter,
            },
            "risk_signals": risk_signals,
            "task_candidates": task_candidates,
        }

    async def _persist_analysis(self, session: AsyncSession, state: FanProfileState) -> dict[str, Any]:
        source = state.get("analysis_source", "rules")
        input_payload = {
            key: state.get(key)
            for key in (
                "fan_token_balance",
                "completed_tasks",
                "active_days",
                "referrals",
                "onchain_actions",
                "chain_summary",
                "risk_signals",
            )
        }
        output_payload = {
            "run_id": state["run_id"],
            "wallet_address": state["wallet_address"],
            "scores": state["scores"],
            "fan_type": state["fan_type"],
            "labels": state["labels"],
            "risk_level": state["risk_level"],
            "summary": state["summary"],
            "analysis_source": source,
            "badge_eligible": state["badge_eligible"],
            "badge_draft": state.get("badge_draft"),
            "recommended_tasks": state.get("recommended_tasks", []),
        }
        session.add(
            FanProfileRun(
                user_id=state.get("user_id"),
                wallet_address=state["wallet_address"],
                community_id="global",
                input_payload=input_payload,
                output_payload=output_payload,
                analysis_source=source,
                rule_version="fan-profile-v3",
                prompt_version="fan-profile-prompt-v3",
                model_id=settings.openai_model if source == "llm" else "rules",
                degraded=source == "rules" and self.model_service.available,
            )
        )
        persisted_user_id = state.get("user_id")
        if persisted_user_id:
            profile = await session.get(UserProfile, persisted_user_id)
            if profile is not None:
                profile.fan_type = state["fan_type"]
                profile.updated_at = utc_now()
        await session.commit()
        return {}

    def _to_analysis(self, run_id: str, result: dict[str, Any]) -> FanProfileAnalysis:
        source = result.get("analysis_source", "rules")
        return FanProfileAnalysis(
            run_id=run_id,
            wallet_address=result["wallet_address"],
            scores=FanProfileScores(**result["scores"]),
            fan_type=result["fan_type"],
            labels=result["labels"],
            risk_level=result["risk_level"],
            summary=result["summary"],
            analysis_source=source,
            degraded=source == "rules" and self.model_service.available,
            rule_version="fan-profile-v3",
            prompt_version="fan-profile-prompt-v3",
            model_id=settings.openai_model if source == "llm" else "rules",
            badge_eligible=result["badge_eligible"],
            badge_draft=BadgeDraft(**result["badge_draft"]) if result.get("badge_draft") else None,
            recommended_tasks=[TaskRecommendation(**item) for item in result.get("recommended_tasks", [])],
        )

    async def analyze(
        self,
        request: FanProfileRequest,
        *,
        session: AsyncSession | None = None,
        user_id: str | None = None,
    ) -> FanProfileAnalysis:
        run_id = str(uuid4())
        config: RunnableConfig = {"configurable": {"thread_id": run_id}}
        if session is None:
            await self.initialize()
            graph = self._graph
            if graph is None:
                raise RuntimeError("fan profile graph failed to initialize")
        else:
            graph = build_fan_profile_graph(
                self.model_service,
                persist_result=lambda state: self._persist_analysis(session, state),
            )
        try:
            result = await graph.ainvoke(
                {**request.model_dump(), "run_id": run_id, "user_id": user_id},
                config=config,
            )
            source = result.get("analysis_source", "rules")
            fan_profile_runs_total.labels(source, "success").inc()
            return self._to_analysis(run_id, result)
        except Exception:
            fan_profile_runs_total.labels("unknown", "error").inc()
            raise

    async def analyze_user(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        wallet_address: str,
    ) -> FanProfileAnalysis:
        run_id = str(uuid4())
        graph = build_fan_profile_graph(
            self.model_service,
            prepare_data=lambda state: self._prepare_user_data(session, user_id, wallet_address, state),
            persist_result=lambda state: self._persist_analysis(session, state),
        )
        config: RunnableConfig = {"configurable": {"thread_id": run_id}}
        try:
            result = await graph.ainvoke(
                {"run_id": run_id, "user_id": user_id, "wallet_address": wallet_address},
                config=config,
            )
            source = result.get("analysis_source", "rules")
            fan_profile_runs_total.labels(source, "success").inc()
            return self._to_analysis(run_id, result)
        except Exception:
            fan_profile_runs_total.labels("unknown", "error").inc()
            raise


fan_profile_agent = FanProfileAgent()
