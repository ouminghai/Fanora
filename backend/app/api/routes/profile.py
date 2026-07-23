"""Current user's persisted, database-backed fan profile."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.fan_profile import fan_profile_agent
from app.core.database import get_database_session
from app.core.security import get_current_identity
from app.schemas.fan_profile import FanProfileAnalysis
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
