"""Protected Agent endpoints."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.fan_profile import fan_profile_agent
from app.core.config import settings
from app.core.database import get_database_session
from app.core.limiter import limiter
from app.core.security import require_internal_api_key
from app.schemas.fan_profile import FanProfileAnalysis, FanProfileRequest

router = APIRouter(prefix="/agent", dependencies=[Depends(require_internal_api_key)])


@router.post("/fan-profile/analyze", response_model=FanProfileAnalysis)
@limiter.limit(settings.rate_limit_agent)
async def analyze_fan_profile(
    request: Request,
    payload: FanProfileRequest,
    session: AsyncSession = Depends(get_database_session),
) -> FanProfileAnalysis:
    return await fan_profile_agent.analyze(payload, session=session)
