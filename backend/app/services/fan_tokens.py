"""Deterministic, idempotent Fan Token ledger operations."""

import asyncio
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlmodel import col, func, select

from app.core.logging import logger
from app.models.community import FanTokenLedger
from app.models.membership import FanTokenRule, MembershipLevel
from app.models.user import UserProfile, Wallet

MEMBERSHIP_CARD_SYNC_KEY = "membership_card_sync_user_ids"
_pending_card_sync_users: set[str] = set()
_active_card_sync_users: set[str] = set()
_card_sync_tasks: set[asyncio.Task[None]] = set()


def request_membership_card_sync(session: AsyncSession, user_id: str) -> None:
    session.info.setdefault(MEMBERSHIP_CARD_SYNC_KEY, set()).add(user_id)


async def _sync_membership_card_after_commit(user_id: str) -> None:
    from app.core.database import database_service
    from app.services.identity import AuthenticatedIdentity
    from app.services.nft import nft_service

    try:
        while user_id in _pending_card_sync_users:
            _pending_card_sync_users.discard(user_id)
            async with database_service.session_factory() as session:
                profile = await session.get(UserProfile, user_id)
                wallet = (
                    await session.execute(
                        select(Wallet).where(
                            Wallet.user_id == user_id,
                            col(Wallet.is_primary).is_(True),
                        )
                    )
                ).scalar_one_or_none()
                if profile is None or not profile.is_official_member or wallet is None:
                    continue
                wallet_type = wallet.wallet_type
                if wallet_type not in ("embedded", "external"):
                    logger.warning(
                        "automatic_membership_card_sync_skipped_invalid_wallet_type",
                        user_id=user_id,
                        wallet_type=wallet_type,
                    )
                    continue
                identity = AuthenticatedIdentity(
                    user_id=user_id,
                    primary_wallet=wallet.address,
                    wallet_type=wallet_type,
                    provider=wallet.provider or "fanora",
                )
                try:
                    await nft_service.create_membership_card(session, identity)
                except Exception:
                    await session.rollback()
                    logger.exception("automatic_membership_card_sync_failed", user_id=user_id)
    finally:
        _active_card_sync_users.discard(user_id)


@event.listens_for(Session, "after_commit")
def _schedule_membership_card_sync(sync_session: Session) -> None:
    user_ids = sync_session.info.pop(MEMBERSHIP_CARD_SYNC_KEY, set())
    if not user_ids:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    for user_id in user_ids:
        _pending_card_sync_users.add(user_id)
        if user_id in _active_card_sync_users:
            continue
        _active_card_sync_users.add(user_id)
        task = loop.create_task(_sync_membership_card_after_commit(user_id))
        _card_sync_tasks.add(task)
        task.add_done_callback(_card_sync_tasks.discard)


@event.listens_for(Session, "after_rollback")
def _discard_membership_card_sync(sync_session: Session) -> None:
    sync_session.info.pop(MEMBERSHIP_CARD_SYNC_KEY, None)


class FanTokenService:
    async def _sync_level(self, session: AsyncSession, profile: UserProfile) -> None:
        if profile.level == "神经领袖":
            return
        earned_level = (
            await session.execute(
                select(MembershipLevel)
                .where(
                    col(MembershipLevel.is_active).is_(True),
                    col(MembershipLevel.is_management).is_(False),
                    col(MembershipLevel.min_token_balance) <= profile.fan_token_lifetime_earned,
                    (col(MembershipLevel.max_token_balance).is_(None))
                    | (col(MembershipLevel.max_token_balance) >= profile.fan_token_lifetime_earned),
                )
                .order_by(col(MembershipLevel.rank).desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if earned_level is None:
            return
        current_level = (
            await session.execute(
                select(MembershipLevel).where(MembershipLevel.name == profile.level)
            )
        ).scalar_one_or_none()
        if current_level is None or earned_level.name != profile.level:
            profile.level = earned_level.name

    async def sync_level(self, session: AsyncSession, profile: UserProfile) -> bool:
        """Sync a profile level from lifetime earned FAN, independent of spendable balance."""
        previous_level = profile.level
        await self._sync_level(session, profile)
        if profile.is_official_member and profile.level != previous_level:
            request_membership_card_sync(session, profile.user_id)
        return profile.level != previous_level

    async def award(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        delta: int,
        source_type: str,
        source_id: str | None,
        idempotency_key: str,
        description: str,
        task_id: str | None = None,
    ) -> FanTokenLedger:
        profile = await session.get(UserProfile, user_id, with_for_update=True)
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found")
        existing = (
            await session.execute(select(FanTokenLedger).where(FanTokenLedger.idempotency_key == idempotency_key))
        ).scalar_one_or_none()
        if existing is not None:
            return existing
        balance_after = profile.fan_token_balance + delta
        if balance_after < 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Fan Token adjustment would make the balance negative",
            )
        profile.fan_token_balance = balance_after
        if delta > 0:
            profile.fan_token_lifetime_earned += delta
        await self.sync_level(session, profile)
        entry = FanTokenLedger(
            user_id=user_id,
            delta=delta,
            balance_after=balance_after,
            source_type=source_type,
            source_id=source_id,
            task_id=task_id,
            idempotency_key=idempotency_key,
            description=description,
        )
        session.add(entry)
        await session.flush()
        return entry

    async def award_rule(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        rule_code: str,
        source_id: str,
        idempotency_key: str,
        fallback_delta: int,
        fallback_description: str,
    ) -> FanTokenLedger | None:
        rule = await session.get(FanTokenRule, rule_code)
        if rule is not None and not rule.is_active:
            return None
        delta = rule.token_delta if rule is not None else fallback_delta
        description = rule.name if rule is not None else fallback_description
        now = datetime.now(UTC)
        if rule is not None and rule.daily_limit is not None:
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            today_count = (
                await session.execute(
                    select(func.count(col(FanTokenLedger.id))).where(
                        FanTokenLedger.user_id == user_id,
                        FanTokenLedger.source_type == f"rule:{rule_code}",
                        FanTokenLedger.created_at >= today_start,
                    )
                )
            ).scalar_one()
            if today_count >= rule.daily_limit:
                return None
        if rule is not None and rule.monthly_limit is not None:
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_count = (
                await session.execute(
                    select(func.count(col(FanTokenLedger.id))).where(
                        FanTokenLedger.user_id == user_id,
                        FanTokenLedger.source_type == f"rule:{rule_code}",
                        FanTokenLedger.created_at >= month_start,
                    )
                )
            ).scalar_one()
            if month_count >= rule.monthly_limit:
                return None
        return await self.award(
            session,
            user_id=user_id,
            delta=delta,
            source_type=f"rule:{rule_code}",
            source_id=source_id,
            idempotency_key=idempotency_key,
            description=description,
        )


fan_token_service = FanTokenService()
