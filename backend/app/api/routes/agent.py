"""Protected Agent endpoints."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.fan_profile import fan_profile_agent
from app.core.config import settings
from app.core.database import get_database_session
from app.core.limiter import limiter
from app.core.security import require_internal_api_key
from app.models.fan_profile import FanProfileRun
from app.schemas.fan_profile import FanProfileAnalysis, FanProfileRequest

router = APIRouter(prefix="/agent", dependencies=[Depends(require_internal_api_key)])


@router.post("/fan-profile/analyze", response_model=FanProfileAnalysis)
@limiter.limit(settings.rate_limit_agent)
async def analyze_fan_profile(
    request: Request,
    payload: FanProfileRequest,
    session: AsyncSession = Depends(get_database_session),
) -> FanProfileAnalysis:
    analysis = await fan_profile_agent.analyze(payload)
    session.add(
        FanProfileRun(
            wallet_address=analysis.wallet_address,
            community_id="global",
            input_payload=payload.model_dump(),
            output_payload=analysis.model_dump(),
            analysis_source=analysis.analysis_source,
            rule_version=analysis.rule_version,
            prompt_version=analysis.prompt_version,
            model_id=analysis.model_id,
            degraded=analysis.degraded,
        )
    )
    await session.commit()
    return analysis
