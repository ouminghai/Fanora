"""Rules, settlement, generation, and audit trail for NFT Memory Forge."""

import hashlib
import math
import secrets
from datetime import UTC, datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from app.agents.nft_visual_templates import (
    NFT_FORGE_ANALYSIS_SYSTEM_PROMPT,
    NFT_FORGE_ANALYSIS_USER_PROMPT_TEMPLATE,
)
from app.core.config import settings
from app.core.logging import logger
from app.models.base import utc_now
from app.models.membership import MembershipLevel
from app.models.nft import (
    FragmentLedger,
    NftAiAnalysis,
    NftForgeAttempt,
    NftForgeSession,
    UserFragmentBalance,
)
from app.models.user import UserProfile
from app.schemas.nft_forge import (
    NftForgeAnalysisResponse,
    NftForgeAnalyzeRequest,
    NftForgeAttemptResponse,
    NftForgeProbabilityResponse,
    NftForgeSessionResponse,
    NftForgeStrategyRequest,
    NftFragmentBalanceResponse,
    NftFragmentLedgerResponse,
    NftFragmentRedeemRequest,
)
from app.services.fan_tokens import fan_token_service
from app.services.llm import llm_service
from app.services.llm.service import LLMUnavailable


class ForgeValidationError(ValueError):
    pass


class ForgeAnalysisDraft(BaseModel):
    originality: int = Field(ge=0, le=100)
    visual_quality: int = Field(ge=0, le=100)
    fan_emotion: int = Field(ge=0, le=100)
    scarcity: int = Field(ge=0, le=100)
    community_potential: int = Field(ge=0, le=100)
    suggestions: list[str] = Field(default_factory=list, max_length=3)

    @model_validator(mode="before")
    @classmethod
    def flatten_scores_object(cls, value: object) -> object:
        """Accept the nested scores shape occasionally returned by the LLM."""

        if not isinstance(value, dict) or not isinstance(value.get("scores"), dict):
            return value
        scores = value["scores"]
        return {
            **scores,
            **{key: item for key, item in value.items() if key != "scores"},
        }


MODE_RULES: dict[str, dict[str, Any]] = {
    "STABLE": {"modifier": 15.0, "possible": ["发行成功", "发行失败"]},
    "FOCUSED": {"modifier": 0.0, "possible": ["发行成功", "发行失败"]},
    "LEGENDARY": {"modifier": -15.0, "possible": ["发行成功", "发行失败"]},
}

MARKET_EXPOSURE_RATE_PER_DECADE = 0.75


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _rarity_for_score(score: int) -> str:
    if score >= 90:
        return "Legendary"
    if score >= 80:
        return "Rare"
    if score >= 65:
        return "Special"
    if score >= 40:
        return "Normal"
    return "Draft"


def _recommendations(score: int) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    if score >= 90:
        return (1, 25, 10), (30, 100, 50)
    if score >= 80:
        return (10, 100, 50), (20, 60, 30)
    if score >= 65:
        return (50, 300, 100), (10, 40, 20)
    if score >= 40:
        return (100, 500, 200), (5, 25, 10)
    return (200, 500, 300), (1, 15, 5)


def _fit(value: int, minimum: int, maximum: int, positive: float, negative: float) -> float:
    if minimum <= value <= maximum:
        midpoint = (minimum + maximum) / 2
        half_range = max((maximum - minimum) / 2, 1)
        return round(positive - abs(value - midpoint) / half_range * (positive * 0.35), 2)
    distance = minimum - value if value < minimum else value - maximum
    scale = max(maximum - minimum, minimum, 1)
    return round(_clamp(positive - (distance / scale) * (positive - negative), negative, positive), 2)


def _market_exposure_multiplier(forge: NftForgeSession, analysis: NftAiAnalysis) -> float:
    recommended_exposure = max(
        analysis.recommend_supply_default * analysis.recommend_price_default,
        1,
    )
    exposure_ratio = (forge.supply * forge.price_fan_tokens) / recommended_exposure
    if exposure_ratio <= 1:
        return 1.0
    return MARKET_EXPOSURE_RATE_PER_DECADE ** math.log10(exposure_ratio)


def _forge_analysis_messages(payload: NftForgeAnalyzeRequest) -> list[SystemMessage | HumanMessage]:
    text = NFT_FORGE_ANALYSIS_USER_PROMPT_TEMPLATE.format(
        title=payload.title,
        story_summary=payload.story_summary,
        image_prompt=payload.image_prompt,
        visual_style=payload.visual_style,
        reference_count=len(payload.reference_image_urls),
        supply=payload.supply,
        price_fan_tokens=payload.price_fan_tokens,
        attributes="、".join(f"{item.trait_type}:{item.value}" for item in payload.suggested_attributes) or "暂无",
    )
    return [
        SystemMessage(content=NFT_FORGE_ANALYSIS_SYSTEM_PROMPT),
        HumanMessage(
            content=[
                {"type": "text", "text": text},
                {"type": "image_url", "image_url": {"url": payload.image_url}},
            ]
        ),
    ]


class NftForgeService:
    def _mode_cost(self, mode: str) -> int:
        return {
            "STABLE": settings.nft_forge_stable_cost,
            "FOCUSED": settings.nft_forge_focused_cost,
            "LEGENDARY": settings.nft_forge_legendary_cost,
        }[mode]

    def _fallback_analysis(self, payload: NftForgeAnalyzeRequest) -> ForgeAnalysisDraft:
        story_length = len(payload.story_summary.strip())
        prompt_length = len(payload.image_prompt.strip())
        personal_terms = sum(
            term in payload.story_summary
            for term in ("我", "我们", "第一次", "那天", "记得", "现场", "票", "信", "性格", "歌曲", "陪伴", "想象")
        )
        emotion_terms = sum(
            term in payload.story_summary for term in ("喜欢", "感动", "勇气", "陪伴", "梦想", "难忘", "思念", "热爱")
        )
        originality = int(_clamp(43 + min(story_length / 12, 24) + personal_terms * 3, 0, 100))
        visual_quality = int(
            _clamp(40 + min(prompt_length / 28, 28) + len(payload.reference_image_urls) * 6, 0, 100)
        )
        fan_emotion = int(_clamp(42 + min(story_length / 10, 28) + emotion_terms * 4, 0, 100))
        scarcity = int(_clamp(42 + personal_terms * 5 + (8 if payload.supply <= 100 else 0), 0, 100))
        community = int(_clamp(45 + min(story_length / 18, 20) + len(payload.suggested_attributes) * 3, 0, 100))
        suggestions: list[str] = []
        if story_length < 80:
            suggestions.append("补充一个具体感受、性格特征、歌曲带来的画面或生活细节")
        if not payload.reference_image_urls:
            suggestions.append("加入一张有权使用的参考图，明确材质和构图方向")
        if prompt_length < 180:
            suggestions.append("补充主视觉、前中后景、光线和收藏品工艺")
        if not suggestions:
            suggestions.append("保留当前故事核心，并让象征物成为画面第一视觉焦点")
        return ForgeAnalysisDraft(
            originality=originality,
            visual_quality=visual_quality,
            fan_emotion=fan_emotion,
            scarcity=scarcity,
            community_potential=community,
            suggestions=suggestions[:3],
        )

    async def _analyze_dimensions(self, payload: NftForgeAnalyzeRequest) -> tuple[ForgeAnalysisDraft, str]:
        fallback = self._fallback_analysis(payload)
        if not llm_service.available:
            return fallback, "rules"
        try:
            result = await llm_service.call_structured(
                _forge_analysis_messages(payload),
                ForgeAnalysisDraft,
            )
            return result, settings.openai_model or "llm"
        except (LLMUnavailable, ValueError, TypeError):
            logger.exception("nft_forge_analysis_fallback")
            return fallback, "rules"

    async def _level_bonus(self, session: AsyncSession, user_id: str) -> float:
        profile = await session.get(UserProfile, user_id)
        if profile is None:
            return 0.0
        level = (
            await session.execute(select(MembershipLevel).where(MembershipLevel.name == profile.level))
        ).scalar_one_or_none()
        return float(_clamp((level.rank - 1) * 1.5 if level else 0, 0, 8))

    async def probability(
        self, session: AsyncSession, forge: NftForgeSession, analysis: NftAiAnalysis
    ) -> NftForgeProbabilityResponse:
        mode = MODE_RULES[forge.forge_mode]
        strategy_fit = _fit(
            forge.supply,
            analysis.recommend_supply_min,
            analysis.recommend_supply_max,
            10,
            -10,
        )
        price_fit = _fit(
            forge.price_fan_tokens,
            analysis.recommend_price_min,
            analysis.recommend_price_max,
            5,
            -5,
        )
        level_bonus = await self._level_bonus(session, forge.user_id)
        quality_factor = 35 + analysis.rare_score * 0.45
        market_exposure_multiplier = _market_exposure_multiplier(forge, analysis)
        success_rate = _clamp(
            (quality_factor + strategy_fit + price_fit + level_bonus + mode["modifier"])
            * market_exposure_multiplier,
            settings.nft_forge_success_rate_min,
            settings.nft_forge_success_rate_max,
        )
        return NftForgeProbabilityResponse(
            quality_factor=round(quality_factor, 2),
            strategy_fit=strategy_fit,
            price_fit=price_fit,
            level_bonus=level_bonus,
            mode_modifier=mode["modifier"],
            success_rate=round(success_rate, 2),
            perfect_rate=0,
            fan_cost=self._mode_cost(forge.forge_mode),
            possible_results=mode["possible"],
        )

    async def analyze(
        self, session: AsyncSession, user_id: str, payload: NftForgeAnalyzeRequest
    ) -> NftForgeSessionResponse:
        active = (
            await session.execute(
                select(NftForgeSession).where(
                    NftForgeSession.user_id == user_id,
                    col(NftForgeSession.status).in_(["ANALYZING", "FORGING"]),
                )
            )
        ).scalar_one_or_none()
        if active is not None:
            raise ForgeValidationError("当前已有分析或 Forge 正在进行")
        dimensions, model_name = await self._analyze_dimensions(payload)
        rare_score = round(
            dimensions.originality * 0.25
            + dimensions.visual_quality * 0.20
            + dimensions.fan_emotion * 0.25
            + dimensions.scarcity * 0.20
            + dimensions.community_potential * 0.10
        )
        supply_recommendation, price_recommendation = _recommendations(rare_score)
        forge_mode = "STABLE" if rare_score < 65 else "FOCUSED" if rare_score < 90 else "LEGENDARY"
        version_id = secrets.token_hex(12)
        forge = NftForgeSession(
            user_id=user_id,
            conversation_id=payload.conversation_id,
            template_id=payload.template_id,
            visual_style=payload.visual_style,
            title=payload.title.strip(),
            story_summary=payload.story_summary.strip(),
            image_prompt=payload.image_prompt.strip(),
            reference_image_urls=payload.reference_image_urls,
            suggested_attributes=[item.model_dump() for item in payload.suggested_attributes],
            supply=supply_recommendation[2],
            price_fan_tokens=price_recommendation[2],
            forge_mode=forge_mode,
            generated_versions=[
                {
                    "id": version_id,
                    "url": payload.image_url,
                    "label": "AGENT DRAFT",
                    "name": payload.title.strip(),
                    "description": payload.description.strip(),
                    "image_prompt": payload.image_prompt.strip(),
                    "attributes": [item.model_dump() for item in payload.suggested_attributes],
                }
            ],
            selected_version_id=version_id,
            rules_version=settings.nft_forge_rules_version,
        )
        session.add(forge)
        await session.flush()
        analysis = NftAiAnalysis(
            forge_session_id=forge.id,
            rare_score=rare_score,
            rarity_level=_rarity_for_score(rare_score),
            originality=dimensions.originality,
            visual_quality=dimensions.visual_quality,
            fan_emotion=dimensions.fan_emotion,
            scarcity=dimensions.scarcity,
            community_potential=dimensions.community_potential,
            recommend_supply_min=supply_recommendation[0],
            recommend_supply_max=supply_recommendation[1],
            recommend_supply_default=supply_recommendation[2],
            recommend_price_min=price_recommendation[0],
            recommend_price_max=price_recommendation[1],
            recommend_price_default=price_recommendation[2],
            suggestions=dimensions.suggestions,
            model_name=model_name,
        )
        session.add(analysis)
        await session.commit()
        return await self.response(session, forge, analysis=analysis)

    async def update_strategy(
        self,
        session: AsyncSession,
        user_id: str,
        session_id: str,
        payload: NftForgeStrategyRequest,
    ) -> NftForgeSessionResponse:
        forge = await self._owned_session(session, user_id, session_id, lock=True)
        analysis = await self._analysis(session, forge.id)
        if forge.status in ("FORGING", "PUBLISHED"):
            raise ForgeValidationError("当前状态不能修改 Forge 策略")
        if payload.forge_mode == "LEGENDARY" and analysis.rare_score < 40:
            raise ForgeValidationError("RareScore 低于 40 时暂不能使用 Legendary Forge")
        forge.supply = payload.supply
        forge.price_fan_tokens = payload.price_fan_tokens
        forge.forge_mode = payload.forge_mode
        forge.status = "ANALYZED"
        forge.updated_at = utc_now()
        await session.commit()
        return await self.response(session, forge, analysis=analysis)

    async def _fragment_balance(
        self, session: AsyncSession, user_id: str, *, lock: bool = False
    ) -> UserFragmentBalance:
        balance = (
            await session.execute(
                select(UserFragmentBalance).where(UserFragmentBalance.user_id == user_id).with_for_update()
                if lock
                else select(UserFragmentBalance).where(UserFragmentBalance.user_id == user_id)
            )
        ).scalar_one_or_none()
        if balance is None:
            balance = UserFragmentBalance(user_id=user_id)
            session.add(balance)
            await session.flush()
        return balance

    async def _award_fragment(
        self, session: AsyncSession, user_id: str, attempt: NftForgeAttempt
    ) -> None:
        key = f"nft-forge-fragment:{attempt.id}"
        existing = (
            await session.execute(select(FragmentLedger).where(FragmentLedger.idempotency_key == key))
        ).scalar_one_or_none()
        if existing is not None:
            return
        balance = await self._fragment_balance(session, user_id, lock=True)
        balance.balance += 1
        balance.updated_at = utc_now()
        session.add(
            FragmentLedger(
                user_id=user_id,
                forge_attempt_id=attempt.id,
                delta=1,
                balance_after=balance.balance,
                source_type="FORGE_FAILED",
                idempotency_key=key,
                description="Forge 未完成，获得 1 个 Memory Fragment",
            )
        )

    async def _consume_credit(self, balance: UserFragmentBalance, mode: str) -> None:
        if mode == "STABLE" and balance.stable_credits > 0:
            balance.stable_credits -= 1
        elif mode == "FOCUSED" and balance.focused_credits > 0:
            balance.focused_credits -= 1
        else:
            raise ForgeValidationError(f"没有可用的 {mode.title()} 免费 Forge 次数")
        balance.updated_at = utc_now()

    async def _restore_credit(self, balance: UserFragmentBalance, mode: str) -> None:
        if mode == "STABLE":
            balance.stable_credits += 1
        elif mode == "FOCUSED":
            balance.focused_credits += 1
        balance.updated_at = utc_now()

    async def start(
        self,
        session: AsyncSession,
        user_id: str,
        session_id: str,
        idempotency_key: str,
        *,
        use_fragment_credit: bool,
    ) -> NftForgeSessionResponse:
        existing = (
            await session.execute(
                select(NftForgeAttempt).where(NftForgeAttempt.idempotency_key == idempotency_key)
            )
        ).scalar_one_or_none()
        if existing is not None:
            if existing.user_id != user_id or existing.forge_session_id != session_id:
                raise ForgeValidationError("幂等键已被其他 Forge 请求使用")
            forge = await self._owned_session(session, user_id, session_id)
            return await self.response(session, forge)

        forge = await self._owned_session(session, user_id, session_id, lock=True)
        if forge.status not in ("ANALYZED", "FAILED", "ERROR"):
            raise ForgeValidationError("当前会话尚不能开始 Forge")
        if not forge.selected_version_id or not any(
            item.get("id") == forge.selected_version_id for item in forge.generated_versions
        ):
            raise ForgeValidationError("Agent 图片尚未准备好，不能进行发行判定")
        active = (
            await session.execute(
                select(NftForgeSession).where(
                    NftForgeSession.user_id == user_id,
                    NftForgeSession.id != forge.id,
                    NftForgeSession.status == "FORGING",
                )
            )
        ).scalar_one_or_none()
        if active is not None:
            raise ForgeValidationError("同一时间只能进行一个 Forge")
        today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        daily_count = (
            await session.execute(
                select(func.count(col(NftForgeAttempt.id))).where(
                    NftForgeAttempt.user_id == user_id,
                    NftForgeAttempt.created_at >= today,
                )
            )
        ).scalar_one()
        if daily_count >= settings.nft_forge_daily_limit:
            raise ForgeValidationError(f"今日 Forge 次数已达到 {settings.nft_forge_daily_limit} 次上限")
        analysis = await self._analysis(session, forge.id)
        probability = await self.probability(session, forge, analysis)
        seed = secrets.token_hex(32)
        seed_hash = hashlib.sha256(seed.encode()).hexdigest()
        random_roll = self._roll(seed, "success")
        payment_source = "FRAGMENT" if use_fragment_credit else "FAN"
        fan_cost = 0 if use_fragment_credit else probability.fan_cost
        attempt = NftForgeAttempt(
            forge_session_id=forge.id,
            user_id=user_id,
            idempotency_key=idempotency_key,
            forge_mode=forge.forge_mode,
            payment_source=payment_source,
            fan_cost=fan_cost,
            success_rate=probability.success_rate,
            perfect_rate=0,
            random_roll=random_roll,
            perfect_roll=None,
            server_seed_hash=seed_hash,
            rules_version=forge.rules_version,
        )
        session.add(attempt)
        forge.status = "FORGING"
        forge.updated_at = utc_now()
        balance = await self._fragment_balance(session, user_id, lock=True)
        if use_fragment_credit:
            await self._consume_credit(balance, forge.forge_mode)
        else:
            await fan_token_service.award(
                session,
                user_id=user_id,
                delta=-fan_cost,
                source_type="nft-forge-spend",
                source_id=forge.id,
                idempotency_key=f"nft-forge-spend:{attempt.id}",
                description=f"{forge.forge_mode.title()} Forge 消耗",
            )
        await session.commit()

        if random_roll > probability.success_rate:
            attempt.result = "FAILED"
            attempt.server_seed_reveal = seed
            attempt.completed_at = utc_now()
            forge.status = "FAILED"
            forge.updated_at = utc_now()
            await self._award_fragment(session, user_id, attempt)
            await session.commit()
            return await self.response(session, forge, analysis=analysis)

        attempt.result = "SUCCESS"
        attempt.server_seed_reveal = seed
        attempt.completed_at = utc_now()
        forge.status = "SUCCESS"
        forge.updated_at = utc_now()
        await session.commit()
        return await self.response(session, forge, analysis=analysis)

    @staticmethod
    def _roll(seed: str, namespace: str) -> float:
        digest = hashlib.sha256(f"{seed}:{namespace}".encode()).digest()
        return round((int.from_bytes(digest[:8], "big") % 1_000_000) / 10_000, 4)

    async def select_version(
        self, session: AsyncSession, user_id: str, session_id: str, version_id: str
    ) -> NftForgeSessionResponse:
        forge = await self._owned_session(session, user_id, session_id, lock=True)
        if forge.status not in ("SUCCESS", "PERFECT"):
            raise ForgeValidationError("只有成功 Forge 的草稿可以选择版本")
        if not any(item.get("id") == version_id for item in forge.generated_versions):
            raise ForgeValidationError("图片版本不存在")
        forge.selected_version_id = version_id
        forge.updated_at = utc_now()
        await session.commit()
        return await self.response(session, forge)

    async def redeem(
        self, session: AsyncSession, user_id: str, payload: NftFragmentRedeemRequest
    ) -> NftFragmentBalanceResponse:
        existing = (
            await session.execute(select(FragmentLedger).where(FragmentLedger.idempotency_key == payload.idempotency_key))
        ).scalar_one_or_none()
        if existing is not None:
            return await self.fragments(session, user_id)
        cost = (
            settings.nft_forge_stable_fragment_cost
            if payload.forge_mode == "STABLE"
            else settings.nft_forge_focused_fragment_cost
        )
        balance = await self._fragment_balance(session, user_id, lock=True)
        if balance.balance < cost:
            raise ForgeValidationError(f"兑换 {payload.forge_mode.title()} Forge 需要 {cost} 个 Fragment")
        balance.balance -= cost
        if payload.forge_mode == "STABLE":
            balance.stable_credits += 1
        else:
            balance.focused_credits += 1
        balance.updated_at = utc_now()
        session.add(
            FragmentLedger(
                user_id=user_id,
                delta=-cost,
                balance_after=balance.balance,
                source_type="REDEEM",
                idempotency_key=payload.idempotency_key,
                description=f"兑换 1 次免费 {payload.forge_mode.title()} Forge",
            )
        )
        await session.commit()
        return await self.fragments(session, user_id)

    async def fragments(self, session: AsyncSession, user_id: str) -> NftFragmentBalanceResponse:
        balance = await self._fragment_balance(session, user_id)
        ledger = list(
            (
                await session.execute(
                    select(FragmentLedger)
                    .where(FragmentLedger.user_id == user_id)
                    .order_by(col(FragmentLedger.created_at).desc())
                    .limit(20)
                )
            ).scalars()
        )
        return NftFragmentBalanceResponse(
            balance=balance.balance,
            stable_credits=balance.stable_credits,
            focused_credits=balance.focused_credits,
            stable_redeem_cost=settings.nft_forge_stable_fragment_cost,
            focused_redeem_cost=settings.nft_forge_focused_fragment_cost,
            ledger=[
                NftFragmentLedgerResponse(
                    id=item.id,
                    delta=item.delta,
                    balance_after=item.balance_after,
                    source_type=item.source_type,
                    description=item.description,
                    created_at=item.created_at,
                )
                for item in ledger
            ],
        )

    async def get(self, session: AsyncSession, user_id: str, session_id: str) -> NftForgeSessionResponse:
        return await self.response(session, await self._owned_session(session, user_id, session_id))

    async def _owned_session(
        self, session: AsyncSession, user_id: str, session_id: str, *, lock: bool = False
    ) -> NftForgeSession:
        statement = select(NftForgeSession).where(
            NftForgeSession.id == session_id,
            NftForgeSession.user_id == user_id,
        )
        if lock:
            statement = statement.with_for_update()
        forge = (await session.execute(statement)).scalar_one_or_none()
        if forge is None:
            raise ForgeValidationError("Forge 会话不存在")
        return forge

    async def _analysis(self, session: AsyncSession, session_id: str) -> NftAiAnalysis:
        analysis = (
            await session.execute(select(NftAiAnalysis).where(NftAiAnalysis.forge_session_id == session_id))
        ).scalar_one_or_none()
        if analysis is None:
            raise ForgeValidationError("Forge 分析结果不存在")
        return analysis

    async def response(
        self,
        session: AsyncSession,
        forge: NftForgeSession,
        *,
        analysis: NftAiAnalysis | None = None,
    ) -> NftForgeSessionResponse:
        analysis = analysis or await self._analysis(session, forge.id)
        latest_attempt = (
            (
                await session.execute(
                    select(NftForgeAttempt)
                    .where(NftForgeAttempt.forge_session_id == forge.id)
                    .order_by(col(NftForgeAttempt.created_at).desc())
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
        fragments = await self._fragment_balance(session, forge.user_id)
        profile = await session.get(UserProfile, forge.user_id)
        probability = await self.probability(session, forge, analysis)
        return NftForgeSessionResponse(
            id=forge.id,
            conversation_id=forge.conversation_id,
            status=forge.status,
            title=forge.title,
            story_summary=forge.story_summary,
            image_prompt=forge.image_prompt,
            reference_image_urls=forge.reference_image_urls,
            suggested_attributes=forge.suggested_attributes,
            supply=forge.supply,
            price_fan_tokens=forge.price_fan_tokens,
            forge_mode=forge.forge_mode,
            rules_version=forge.rules_version,
            generated_versions=forge.generated_versions,
            selected_version_id=forge.selected_version_id,
            analysis=NftForgeAnalysisResponse(
                rare_score=analysis.rare_score,
                rarity_level=analysis.rarity_level,
                dimensions={
                    "originality": analysis.originality,
                    "visual_quality": analysis.visual_quality,
                    "fan_emotion": analysis.fan_emotion,
                    "scarcity": analysis.scarcity,
                    "community_potential": analysis.community_potential,
                },
                recommend_supply={
                    "min": analysis.recommend_supply_min,
                    "max": analysis.recommend_supply_max,
                    "default": analysis.recommend_supply_default,
                },
                recommend_price={
                    "min": analysis.recommend_price_min,
                    "max": analysis.recommend_price_max,
                    "default": analysis.recommend_price_default,
                },
                suggestions=analysis.suggestions,
                model_name=analysis.model_name,
                prompt_version=analysis.prompt_version,
            ),
            probability=probability,
            latest_attempt=(
                NftForgeAttemptResponse(
                    id=latest_attempt.id,
                    forge_mode=latest_attempt.forge_mode,
                    payment_source=latest_attempt.payment_source,
                    fan_cost=latest_attempt.fan_cost,
                    success_rate=latest_attempt.success_rate,
                    perfect_rate=latest_attempt.perfect_rate,
                    random_roll=latest_attempt.random_roll,
                    perfect_roll=latest_attempt.perfect_roll,
                    server_seed_hash=latest_attempt.server_seed_hash,
                    server_seed_reveal=latest_attempt.server_seed_reveal,
                    result=latest_attempt.result,
                    refund_status=latest_attempt.refund_status,
                    error_message=latest_attempt.error_message,
                    rules_version=latest_attempt.rules_version,
                    created_at=latest_attempt.created_at,
                    completed_at=latest_attempt.completed_at,
                )
                if latest_attempt
                else None
            ),
            fragment_balance=fragments.balance,
            stable_credits=fragments.stable_credits,
            focused_credits=fragments.focused_credits,
            fan_token_balance=profile.fan_token_balance if profile else 0,
            created_at=forge.created_at,
            updated_at=forge.updated_at,
        )


nft_forge_service = NftForgeService()
