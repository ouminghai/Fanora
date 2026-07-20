"""Deterministic, idempotent Fan Token ledger operations."""

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from app.models.community import FanTokenLedger
from app.models.membership import FanTokenRule, MembershipLevel
from app.models.user import UserProfile


class FanTokenService:
    async def _sync_level(self, session: AsyncSession, profile: UserProfile) -> None:
        if profile.level == "神经领袖":
            return
        level = (
            await session.execute(
                select(MembershipLevel)
                .where(
                    col(MembershipLevel.is_active).is_(True),
                    col(MembershipLevel.is_management).is_(False),
                    col(MembershipLevel.min_token_balance) <= profile.fan_token_balance,
                    (col(MembershipLevel.max_token_balance).is_(None))
                    | (col(MembershipLevel.max_token_balance) >= profile.fan_token_balance),
                )
                .order_by(col(MembershipLevel.rank).desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if level is not None:
            profile.level = level.name

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
        await self._sync_level(session, profile)
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
