"""Web3Auth token verification and Fanora session lifecycle."""

import asyncio
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import HTTPException, status
from jwt import PyJWKClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select
from web3 import Web3

from app.core.config import settings
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
from app.schemas.auth import CommunitySummary, UserResponse, WalletResponse, Web3AuthLoginRequest


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class Web3AuthService:
    def __init__(self) -> None:
        self.jwks_client = PyJWKClient(settings.web3auth_jwks_url, cache_keys=True)

    async def verify_identity_token(self, id_token: str, expected_wallet: str) -> dict[str, Any]:
        def decode() -> dict[str, Any]:
            signing_key = self.jwks_client.get_signing_key_from_jwt(id_token)
            claims = jwt.decode(
                id_token,
                signing_key.key,
                algorithms=["ES256"],
                options={
                    "require": ["exp", "iat", "iss", "aud"],
                    "verify_aud": False,
                    "verify_iss": False,
                },
            )
            issuer = str(claims.get("iss") or "").strip()
            audience = claims.get("aud")
            audiences = {str(value) for value in audience} if isinstance(audience, list) else {str(audience)}
            if not issuer or not any(value and value != "None" for value in audiences):
                raise jwt.InvalidTokenError("Web3Auth issuer or audience is missing")

            if issuer == settings.web3auth_issuer:
                provider_user_id = claims.get("sub") or claims.get("userId") or claims.get("verifierId")
                if settings.web3auth_client_id not in audiences or not provider_user_id:
                    raise jwt.InvalidAudienceError("Web3Auth client audience or subject does not match")
            else:
                if issuer.lower() not in settings.allowed_web3auth_external_issuers:
                    raise jwt.InvalidIssuerError("External wallet issuer is not allowed")
                wallets = claims.get("wallets")
                addresses = {
                    Web3.to_checksum_address(str(wallet.get("address")))
                    for wallet in wallets or []
                    if isinstance(wallet, dict) and Web3.is_address(str(wallet.get("address") or ""))
                }
                if expected_wallet not in addresses:
                    raise jwt.InvalidTokenError("External wallet token does not contain the signed wallet")
            return claims

        try:
            return await asyncio.to_thread(decode)
        except jwt.PyJWTError as error:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Web3Auth identity token") from error
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Web3Auth identity verification is temporarily unavailable",
            ) from error

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

    async def login(
        self, session: AsyncSession, payload: Web3AuthLoginRequest
    ) -> tuple[str, datetime, bool, UserResponse]:
        address = Web3.to_checksum_address(payload.wallet_address)
        challenge = await session.get(LoginChallenge, payload.challenge_id)
        now = utc_now()
        if (
            challenge is None
            or challenge.used_at is not None
            or challenge.wallet_address != address
            or as_utc(challenge.expires_at) <= now
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login challenge is invalid or expired")

        try:
            recovered = Account.recover_message(encode_defunct(text=challenge.message), signature=payload.signature)
        except Exception as error:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid wallet signature") from error
        if Web3.to_checksum_address(recovered) != address:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wallet signature does not match")

        claims = await self.verify_identity_token(payload.id_token, address)
        issuer = str(claims.get("iss") or "").strip()
        provider_user_id = claims.get("sub") or claims.get("userId") or claims.get("verifierId")
        subject = str(provider_user_id or f"{issuer}:{address.lower()}").strip()
        if not subject or len(subject) > 255:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Web3Auth user identifier is missing")

        identity = (
            await session.execute(
                select(AuthIdentity).where(AuthIdentity.provider == "web3auth", AuthIdentity.subject == subject)
            )
        ).scalar_one_or_none()
        wallet = (await session.execute(select(Wallet).where(Wallet.address == address))).scalar_one_or_none()
        is_new_user = identity is None

        if identity is not None:
            user = await session.get(User, identity.user_id)
            if user is None or user.status != "active":
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is not active")
            if wallet is None or wallet.user_id != user.id or not wallet.is_primary:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This login identity is already bound to a different primary wallet",
                )
            profile = await session.get(UserProfile, user.id)
            if profile is None:
                session.add(
                    UserProfile(
                        user_id=user.id,
                        email=str(claims.get("email") or "").strip()[:320] or None,
                        avatar_url=str(claims.get("picture") or claims.get("profileImage") or "").strip()[:2048]
                        or None,
                    )
                )
            role = (
                await session.execute(
                    select(UserRole).where(UserRole.user_id == user.id, UserRole.role == "fan")
                )
            ).scalar_one_or_none()
            if role is None:
                session.add(UserRole(user_id=user.id, role="fan"))
        else:
            if wallet is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This wallet is already bound to another Fanora account",
                )
            display_name = str(claims.get("name") or "").strip()[:80] or None
            user = User(display_name=display_name)
            session.add(user)
            await session.flush()
            session.add(AuthIdentity(user_id=user.id, provider="web3auth", subject=subject))
            wallet = Wallet(
                user_id=user.id,
                address=address,
                wallet_type=payload.wallet_type,
                provider="web3auth",
                is_primary=True,
            )
            session.add(wallet)
            session.add(
                UserProfile(
                    user_id=user.id,
                    email=str(claims.get("email") or "").strip()[:320] or None,
                    avatar_url=str(claims.get("picture") or claims.get("profileImage") or "").strip()[:2048] or None,
                )
            )
            session.add(UserRole(user_id=user.id, role="fan"))

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

        return raw_token, session_expires_at, is_new_user, await build_user_response(session, user.id, include_private=True)


async def build_user_response(session: AsyncSession, user_id: str, *, include_private: bool) -> UserResponse:
    user = await session.get(User, user_id)
    profile = await session.get(UserProfile, user_id)
    wallet = (
        await session.execute(select(Wallet).where(Wallet.user_id == user_id, col(Wallet.is_primary).is_(True)))
    ).scalar_one_or_none()
    if user is None or profile is None or wallet is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User wallet profile is incomplete")
    roles = list(
        (await session.execute(select(UserRole.role).where(UserRole.user_id == user_id))).scalars().all()
    )
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
        level=profile.level,
        fan_token_balance=profile.fan_token_balance,
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


web3auth_service = Web3AuthService()
