"""Wallet signature authentication and Fanora session lifecycle."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select
from web3 import Web3

from app.core.config import settings
from app.core.logging import logger
from app.models.base import utc_now
from app.models.user import (
    AuthIdentity,
    Community,
    CommunityMember,
    LoginChallenge,
    User,
    UserProfile,
    UserRole,
    UserSession,
    Wallet,
)
from app.schemas.auth import CommunitySummary, UserResponse, WalletLoginRequest, WalletResponse


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class WalletAuthService:
    async def create_challenge(self, session: AsyncSession, wallet_address: str) -> LoginChallenge:
        address = Web3.to_checksum_address(wallet_address)
        now = utc_now()
        expires_at = now + timedelta(seconds=settings.auth_challenge_ttl_seconds)
        challenge = LoginChallenge(wallet_address=address, message="", expires_at=expires_at)
        challenge.message = (
            "Fanora wants you to sign in with your wallet:\n"
            f"{address}\n\n"
            "Confirm your wallet identity to continue. This request will not trigger a blockchain transaction.\n\n"
            f"URI: http://localhost:3000\nVersion: 1\nChain ID: {settings.monad_chain_id}\n"
            f"Nonce: {challenge.id}\nIssued At: {now.isoformat()}\nExpiration Time: {expires_at.isoformat()}"
        )
        session.add(challenge)
        await session.commit()
        await session.refresh(challenge)
        return challenge

    async def login_wallet(
        self, session: AsyncSession, payload: WalletLoginRequest
    ) -> tuple[str, datetime, bool, UserResponse]:
        try:
            return await self._login_wallet(session, payload)
        except Exception as error:
            logger.exception(
                "wallet_service_login_failed",
                error_type=type(error).__name__,
                error_message=str(error),
                status_code=getattr(error, "status_code", None),
                error_detail=getattr(error, "detail", None),
                wallet_address=payload.wallet_address,
                challenge_id=payload.challenge_id,
            )
            raise

    async def _login_wallet(
        self, session: AsyncSession, payload: WalletLoginRequest
    ) -> tuple[str, datetime, bool, UserResponse]:
        address, challenge, now = await self._verify_wallet_challenge(
            session,
            payload.challenge_id,
            payload.wallet_address,
            payload.signature,
        )
        wallet = (await session.execute(select(Wallet).where(Wallet.address == address))).scalar_one_or_none()
        identity = (
            await session.execute(
                select(AuthIdentity).where(AuthIdentity.provider == "wallet", AuthIdentity.subject == address.lower())
            )
        ).scalar_one_or_none()
        is_new_user = wallet is None

        if wallet is not None:
            user = await session.get(User, wallet.user_id)
            if user is None or user.status != "active":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is not active")
            if not wallet.is_primary:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Wallet is not the primary login wallet"
                )
            if identity is not None and identity.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Wallet identity belongs to another user"
                )
            if identity is None:
                session.add(AuthIdentity(user_id=user.id, provider="wallet", subject=address.lower()))
            if await session.get(UserProfile, user.id) is None:
                session.add(UserProfile(user_id=user.id))
        else:
            if identity is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="Wallet identity is missing its wallet"
                )
            user = User()
            session.add(user)
            await session.flush()
            session.add(AuthIdentity(user_id=user.id, provider="wallet", subject=address.lower()))
            session.add(
                Wallet(
                    user_id=user.id,
                    address=address,
                    wallet_type="external",
                    provider="rainbowkit",
                    is_primary=True,
                )
            )
            session.add(UserProfile(user_id=user.id))

        role = (
            await session.execute(select(UserRole).where(UserRole.user_id == user.id, UserRole.role == "fan"))
        ).scalar_one_or_none()
        if role is None:
            session.add(UserRole(user_id=user.id, role="fan"))

        return await self._create_session(session, user, challenge, now, is_new_user)

    async def _verify_wallet_challenge(
        self,
        session: AsyncSession,
        challenge_id: str,
        wallet_address: str,
        signature: str,
    ) -> tuple[str, LoginChallenge, datetime]:
        address = Web3.to_checksum_address(wallet_address)
        challenge = await session.get(LoginChallenge, challenge_id)
        now = utc_now()
        if (
            challenge is None
            or challenge.used_at is not None
            or challenge.wallet_address != address
            or as_utc(challenge.expires_at) <= now
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Login challenge is invalid or expired"
            )

        try:
            recovered = Account.recover_message(encode_defunct(text=challenge.message), signature=signature)
        except Exception as error:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid wallet signature") from error
        if Web3.to_checksum_address(recovered) != address:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wallet signature does not match")
        return address, challenge, now

    async def _create_session(
        self,
        session: AsyncSession,
        user: User,
        challenge: LoginChallenge,
        now: datetime,
        is_new_user: bool,
    ) -> tuple[str, datetime, bool, UserResponse]:
        challenge.used_at = now
        user.updated_at = now
        raw_token = secrets.token_urlsafe(48)
        session_expires_at = now + timedelta(seconds=settings.auth_session_ttl_seconds)
        session.add(
            UserSession(
                user_id=user.id,
                token_hash=hash_session_token(raw_token),
                expires_at=session_expires_at,
            )
        )
        try:
            await session.commit()
        except IntegrityError as error:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The login identity or wallet was linked by another request",
            ) from error

        return (
            raw_token,
            session_expires_at,
            is_new_user,
            await build_user_response(session, user.id, include_private=True),
        )


async def build_user_response(session: AsyncSession, user_id: str, *, include_private: bool) -> UserResponse:
    user = await session.get(User, user_id)
    profile = await session.get(UserProfile, user_id)
    wallet = (
        await session.execute(select(Wallet).where(Wallet.user_id == user_id, col(Wallet.is_primary).is_(True)))
    ).scalar_one_or_none()
    if user is None or profile is None or wallet is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User wallet profile is incomplete")
    roles = list((await session.execute(select(UserRole.role).where(UserRole.user_id == user_id))).scalars().all())
    memberships = list(
        (await session.execute(select(CommunityMember).where(CommunityMember.user_id == user_id))).scalars().all()
    )
    community_ids = [membership.community_id for membership in memberships]
    communities: list[Community] = []
    if community_ids:
        communities = list(
            (await session.execute(select(Community).where(col(Community.id).in_(community_ids)))).scalars().all()
        )
    return UserResponse(
        id=user.id,
        display_name=user.display_name,
        username=profile.username,
        email=profile.email if include_private else None,
        avatar_url=profile.avatar_url,
        bio=profile.bio,
        locale=profile.locale,
        level=profile.level if profile.is_official_member else "待入会",
        is_official_member=profile.is_official_member,
        official_member_since=profile.official_member_since,
        fan_token_balance=profile.fan_token_balance,
        fan_token_lifetime_earned=profile.fan_token_lifetime_earned,
        fan_type=profile.fan_type,
        profile_visibility=profile.profile_visibility,
        onboarding_completed=profile.onboarding_completed,
        roles=roles,
        primary_wallet=WalletResponse(
            address=wallet.address,
            wallet_type=wallet.wallet_type,
            provider=wallet.provider,
            is_primary=wallet.is_primary,
        ),
        communities=[
            CommunitySummary(
                id=community.id,
                slug=community.slug,
                name=community.name,
                description=community.description,
                logo_url=community.logo_url,
                owner_user_id=community.owner_user_id,
                is_public=community.is_public,
                joined=True,
            )
            for community in communities
        ],
        created_at=user.created_at,
        updated_at=profile.updated_at,
    )


auth_service = WalletAuthService()
