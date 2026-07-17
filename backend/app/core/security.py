"""Temporary internal authorization until unified user auth is implemented."""

import secrets

from fastapi import Header, HTTPException, status

from app.core.config import Environment, settings


async def require_internal_api_key(x_internal_api_key: str | None = Header(default=None)) -> None:
    if not settings.internal_api_key and settings.environment != Environment.PRODUCTION:
        return
    if not settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Internal API key is not configured"
        )
    if not x_internal_api_key or not secrets.compare_digest(x_internal_api_key, settings.internal_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal API key")
