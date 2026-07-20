"""Internal API-key and unified Fanora user-session authorization."""

import secrets
from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.core.config import Environment, settings
from app.core.database import get_database_session
from app.models.user import User, UserProfile, UserSession, Wallet
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


async def _resolve_identity(
    credentials: HTTPAuthorizationCredentials,
    session: AsyncSession,
) -> AuthenticatedIdentity | None:
    if credentials.scheme.lower() != "bearer":
        return None
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
        return None
    user = await session.get(User, user_session.user_id)
    wallet = (
        await session.execute(
            select(Wallet).where(Wallet.user_id == user_session.user_id, col(Wallet.is_primary).is_(True))
        )
    ).scalar_one_or_none()
    if user is None or user.status != "active" or wallet is None:
        return None
    return AuthenticatedIdentity(
        user_id=user.id,
        primary_wallet=wallet.address,
        wallet_type=wallet.wallet_type,  # type: ignore[arg-type]
        provider=wallet.provider or "web3auth",
    )


async def get_optional_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_database_session),
) -> AuthenticatedIdentity | None:
    if credentials is None:
        return None
    return await _resolve_identity(credentials, session)


async def get_current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_database_session),
) -> AuthenticatedIdentity:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    identity = await _resolve_identity(credentials, session)
    if identity is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session is invalid or expired")
    return identity


async def require_official_member(
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> AuthenticatedIdentity:
    """Require the signed-in user to have a verified 1 MON membership payment."""

    profile = await session.get(UserProfile, identity.user_id)
    if profile is None or not profile.is_official_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Official membership required. Pay 1 MON before joining check-ins or tasks.",
        )
    return identity
