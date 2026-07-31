"""Wallet login, Fanora sessions, and current-user profile endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.adapters.beeimg import BeeImgConfigurationError, BeeImgUploadError, beeimg_adapter
from app.core.config import settings
from app.core.database import get_database_session
from app.core.limiter import limiter
from app.core.logging import logger
from app.core.security import bearer_scheme, get_current_identity
from app.models.base import utc_now
from app.models.user import AuthSecurityEvent, User, UserProfile, UserSession
from app.schemas.auth import (
    AuthChallengeRequest,
    AuthChallengeResponse,
    AuthSessionResponse,
    UserProfileUpdate,
    UserResponse,
    WalletLoginRequest,
)
from app.services.auth import auth_service, build_user_response, hash_session_token
from app.services.identity import AuthenticatedIdentity

router = APIRouter(prefix="/auth")
user_router = APIRouter(prefix="/users")


def client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    return forwarded or (request.client.host if request.client else None)


@router.post("/challenge", response_model=AuthChallengeResponse)
@limiter.limit(settings.rate_limit_auth)
async def create_challenge(
    request: Request,
    payload: AuthChallengeRequest,
    session: AsyncSession = Depends(get_database_session),
) -> AuthChallengeResponse:
    challenge = await auth_service.create_challenge(session, payload.wallet_address)
    session.add(
        AuthSecurityEvent(
            wallet_address=challenge.wallet_address,
            event="challenge_created",
            outcome="success",
            ip_address=client_ip(request),
        )
    )
    await session.commit()
    return AuthChallengeResponse(
        challenge_id=challenge.id,
        message=challenge.message,
        expires_at=challenge.expires_at,
    )


@router.post("/wallet", response_model=AuthSessionResponse)
@limiter.limit(settings.rate_limit_auth)
async def wallet_login(
    request: Request,
    payload: WalletLoginRequest,
    session: AsyncSession = Depends(get_database_session),
) -> AuthSessionResponse:
    try:
        token, expires_at, is_new_user, user = await auth_service.login_wallet(session, payload)
    except HTTPException as error:
        logger.exception(
            "wallet_login_rejected",
            error_type=type(error).__name__,
            error_message=str(error),
            status_code=error.status_code,
            error_detail=error.detail,
            wallet_address=payload.wallet_address,
            challenge_id=payload.challenge_id,
            ip_address=client_ip(request),
        )
        session.add(
            AuthSecurityEvent(
                wallet_address=payload.wallet_address,
                event="wallet_login",
                outcome="rejected",
                ip_address=client_ip(request),
                detail=f"HTTP {error.status_code}",
            )
        )
        await session.commit()
        raise
    session.add(
        AuthSecurityEvent(
            user_id=user.id,
            wallet_address=user.primary_wallet.address,
            event="wallet_login",
            outcome="success",
            ip_address=client_ip(request),
        )
    )
    await session.commit()
    return AuthSessionResponse(
        access_token=token,
        expires_at=expires_at,
        is_new_user=is_new_user,
        user=user,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_database_session),
) -> None:
    user_session = (
        await session.execute(
            select(UserSession).where(
                UserSession.user_id == identity.user_id,
                UserSession.token_hash == hash_session_token(credentials.credentials),
            )
        )
    ).scalar_one_or_none()
    if user_session is not None:
        user_session.revoked_at = utc_now()
        session.add(
            AuthSecurityEvent(
                user_id=identity.user_id,
                wallet_address=identity.primary_wallet,
                event="logout",
                outcome="success",
                ip_address=client_ip(request),
            )
        )
        await session.commit()


@user_router.get("/me", response_model=UserResponse)
async def get_me(
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> UserResponse:
    return await build_user_response(session, identity.user_id, include_private=True)


@user_router.patch("/me", response_model=UserResponse)
async def update_me(
    payload: UserProfileUpdate,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> UserResponse:
    user = await session.get(User, identity.user_id)
    profile = await session.get(UserProfile, identity.user_id)
    if user is None or profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found")
    user.display_name = payload.display_name
    user.updated_at = utc_now()
    profile.username = payload.username
    try:
        profile.avatar_url = await beeimg_adapter.ensure_remote_url(payload.avatar_url, filename="user-avatar")
    except BeeImgConfigurationError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    except (BeeImgUploadError, OSError, ValueError) as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Image upload failed: {error}") from error
    profile.bio = payload.bio
    profile.locale = payload.locale
    profile.profile_visibility = payload.profile_visibility
    profile.onboarding_completed = True
    profile.updated_at = utc_now()
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username is already in use") from error
    return await build_user_response(session, identity.user_id, include_private=True)


@user_router.get("/{user_id}", response_model=UserResponse)
async def get_public_user(
    user_id: str,
    session: AsyncSession = Depends(get_database_session),
) -> UserResponse:
    profile = await session.get(UserProfile, user_id)
    if profile is None or profile.profile_visibility != "public":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Public profile not found")
    return await build_user_response(session, user_id, include_private=False)
