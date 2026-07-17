"""Application and dependency health endpoints."""

from fastapi import APIRouter, Request

from app.agents.fan_profile import fan_profile_agent
from app.core.cache import cache_service
from app.core.config import settings
from app.core.database import database_service
from app.core.limiter import limiter
from app.schemas.common import HealthResponse

router = APIRouter()


async def get_health_status() -> HealthResponse:
    database_healthy = await database_service.health_check()
    return HealthResponse(
        status="healthy" if database_healthy else "degraded",
        version=settings.version,
        environment=settings.environment.value,
        components={
            "api": "healthy",
            "database": "healthy" if database_healthy else "unhealthy",
            "cache": cache_service.backend_name,
            "fan_profile_agent": "ready" if fan_profile_agent._graph is not None else "lazy",
        },
    )


@router.get("/health", response_model=HealthResponse)
@limiter.limit(settings.rate_limit_health)
async def health(request: Request) -> HealthResponse:
    return await get_health_status()
