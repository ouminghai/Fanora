"""Internal API-key and unified Fanora user-session authorization."""

import secrets
from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.core.config import Environment, settings
from app.core.database import get_database_session
from app.models.user import User, UserSession, Wallet
from app.services.auth import as_utc, hash_session_token
from app.services.identity import AuthenticatedIdentity

bearer_scheme = HTTPBearer(auto_error=False)


async def require_internal_api_key(x_internal_api_key: str | None = Header(default=None)) -> None:
    if not settings.internal_api_key and settings.environment != Environment.PRODUCTION:
        return
    if not settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Internal API key is not configured"
        )
    if not x_internal_api_key or not secrets.compare_digest(x_internal_api_key, settings.internal_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid internal API key")


async def get_current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_database_session),
) -> AuthenticatedIdentity:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    user_session = (
        await session.execute(
            select(UserSession).where(UserSession.token_hash == hash_session_token(credentials.credentials))
        )
    ).scalar_one_or_none()
    if (
        user_session is None
        or user_session.revoked_at is not None
        or as_utc(user_session.expires_at) <= datetime.now(UTC)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is invalid or expired")
    user = await session.get(User, user_session.user_id)
    wallet = (
        await session.execute(
            select(Wallet).where(Wallet.user_id == user_session.user_id, col(Wallet.is_primary).is_(True))
        )
    ).scalar_one_or_none()
    if user is None or user.status != "active" or wallet is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Active account with primary wallet required")
    return AuthenticatedIdentity(
        user_id=user.id,
        primary_wallet=wallet.address,
        wallet_type=wallet.wallet_type,  # type: ignore[arg-type]
        provider=wallet.provider or "web3auth",
    )
