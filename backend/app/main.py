"""Fanora FastAPI application with production-oriented infrastructure."""

from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.agents.fan_profile import fan_profile_agent
from app.api.router import api_router
from app.api.routes.health import get_health_status
from app.core.cache import cache_service
from app.core.config import settings
from app.core.database import database_service
from app.core.langgraph.checkpointer import checkpoint_manager
from app.core.limiter import limiter
from app.core.logging import logger
from app.core.middleware import RequestContextMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("application_startup", version=settings.version, environment=settings.environment.value)
    await database_service.initialize()
    await cache_service.initialize()
    await fan_profile_agent.initialize()
    yield
    await checkpoint_manager.close()
    await cache_service.close()
    await database_service.close()
    logger.info("application_shutdown")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Fanora Protocol API and fan-identity Agent backend",
    openapi_url=f"{settings.api_prefix}/openapi.json",
    lifespan=lifespan,
)

app.state.limiter = limiter


async def rate_limit_error_handler(request: Request, error: Exception):
    if not isinstance(error, RateLimitExceeded):
        raise error
    logger.warning(
        "security_rate_limit_exceeded",
        path=request.url.path,
        client_ip=request.client.host if request.client else None,
    )
    return _rate_limit_exceeded_handler(request, error)


app.add_exception_handler(RateLimitExceeded, rate_limit_error_handler)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, error: RequestValidationError) -> JSONResponse:
    logger.warning("request_validation_failed", path=request.url.path, errors=error.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": jsonable_encoder(error.errors())},
    )


app.include_router(api_router, prefix=settings.api_prefix)
app.mount("/metrics", make_asgi_app())


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": settings.app_name, "version": settings.version, "docs": "/docs"}


@app.get("/health")
async def root_health():
    return await get_health_status()
