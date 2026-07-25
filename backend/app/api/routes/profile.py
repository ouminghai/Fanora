"""Database-backed fan-profile analysis for current and public users."""

from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.agents.fan_profile import fan_profile_agent
from app.core.database import get_database_session
from app.core.security import get_current_identity
from app.models.fan_profile import FanProfileRun
from app.models.user import User, UserProfile, Wallet
from app.schemas.fan_profile import (
    FanProfileAnalysis,
    FanProfileScores,
    FanType,
    PublicFanProfileAnalysis,
)
from app.services.identity import AuthenticatedIdentity

router = APIRouter(prefix="/profile")


@router.get("/me", response_model=FanProfileAnalysis)
async def get_my_fan_profile(
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> FanProfileAnalysis:
    return await fan_profile_agent.analyze_user(
        session,
        user_id=identity.user_id,
        wallet_address=identity.primary_wallet,
    )


@router.get("/users/{user_id}", response_model=PublicFanProfileAnalysis)
async def get_public_fan_profile(
    user_id: str,
    session: AsyncSession = Depends(get_database_session),
) -> PublicFanProfileAnalysis:
    user = await session.get(User, user_id)
    profile = await session.get(UserProfile, user_id)
    wallet = (
        await session.execute(
            select(Wallet)
            .where(col(Wallet.user_id) == user_id, col(Wallet.is_primary).is_(True))
            .limit(1)
        )
    ).scalar_one_or_none()
    if user is None or profile is None or wallet is None or profile.profile_visibility != "public":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Public profile not found")
    latest_run = (
        await session.execute(
            select(FanProfileRun)
            .where(col(FanProfileRun.user_id) == user_id)
            .order_by(col(FanProfileRun.created_at).desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest_run is not None:
        try:
            return PublicFanProfileAnalysis.model_validate(latest_run.output_payload)
        except ValidationError:
            pass

    base_score = min(100, profile.fan_token_lifetime_earned // 10)
    public_fan_type = cast(
        FanType,
        profile.fan_type
        if profile.fan_type in {"emerging_fan", "loyal_fan", "advocate", "active_fan", "early_supporter", "high_value_contributor"}
        else "emerging_fan",
    )
    return PublicFanProfileAnalysis(
        scores=FanProfileScores(
            activity=base_score,
            loyalty=min(100, base_score + (10 if profile.is_official_member else 0)),
            influence=0,
            contribution=base_score,
            total=base_score,
        ),
        fan_type=public_fan_type,
        labels=[profile.level, profile.fan_type] + (["正式会员"] if profile.is_official_member else []),
        summary=(
            f"当前为 {profile.level}，累计获得 {profile.fan_token_lifetime_earned} FAN。"
            "画像会随着社区参与、任务贡献和链上行为持续更新。"
        ),
        analysis_source="rules",
        degraded=False,
    )
