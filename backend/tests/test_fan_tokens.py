from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

import app.models.database  # noqa: F401
from app.models.membership import MembershipLevel
from app.models.user import User, UserProfile
from app.services.fan_tokens import MEMBERSHIP_CARD_SYNC_KEY, fan_token_service


@asynccontextmanager
async def fan_token_test_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with factory() as session:
            session.add_all(
                [
                    MembershipLevel(
                        code="newborn",
                        name="新生儿",
                        description="New member",
                        rank=1,
                        min_token_balance=0,
                        max_token_balance=99,
                        badge_image_url="/img/badges/new.png",
                    ),
                    MembershipLevel(
                        code="mild-neuro",
                        name="轻度神经",
                        description="Growing member",
                        rank=2,
                        min_token_balance=100,
                        max_token_balance=499,
                        badge_image_url="/img/badges/mild.png",
                    ),
                ]
            )
            await session.commit()
            yield session
    finally:
        await engine.dispose()


async def test_spending_fan_tokens_preserves_lifetime_progress_and_level() -> None:
    async with fan_token_test_session() as session:
        user = User(display_name="Lifetime FAN Tester")
        session.add(user)
        await session.flush()
        profile = UserProfile(
            user_id=user.id,
            fan_token_balance=90,
            fan_token_lifetime_earned=90,
            level="新生儿",
        )
        session.add(profile)
        await session.flush()

        await fan_token_service.award(
            session,
            user_id=user.id,
            delta=20,
            source_type="test-reward",
            source_id="reward-1",
            idempotency_key=f"test-lifetime-reward:{user.id}",
            description="Test positive FAN reward",
        )
        assert profile.fan_token_balance == 110
        assert profile.fan_token_lifetime_earned == 110
        assert profile.level == "轻度神经"

        await fan_token_service.award(
            session,
            user_id=user.id,
            delta=-100,
            source_type="test-spend",
            source_id="spend-1",
            idempotency_key=f"test-lifetime-spend:{user.id}",
            description="Test FAN redemption",
        )
        assert profile.fan_token_balance == 10
        assert profile.fan_token_lifetime_earned == 110
        assert profile.level == "轻度神经"
        await session.rollback()


async def test_idempotent_reward_only_increases_lifetime_progress_once() -> None:
    async with fan_token_test_session() as session:
        user = User(display_name="Idempotent Lifetime FAN Tester")
        session.add(user)
        await session.flush()
        profile = UserProfile(user_id=user.id)
        session.add(profile)
        await session.flush()
        key = f"test-lifetime-idempotent:{user.id}"

        for _ in range(2):
            await fan_token_service.award(
                session,
                user_id=user.id,
                delta=25,
                source_type="test-reward",
                source_id="reward-2",
                idempotency_key=key,
                description="Test idempotent FAN reward",
            )

        stored = await session.get(UserProfile, user.id)
        assert stored is not None
        assert stored.fan_token_balance == 25
        assert stored.fan_token_lifetime_earned == 25
        await session.rollback()


async def test_official_member_level_change_queues_membership_card_sync() -> None:
    async with fan_token_test_session() as session:
        user = User(display_name="Official Lifetime FAN Tester")
        session.add(user)
        await session.flush()
        profile = UserProfile(
            user_id=user.id,
            fan_token_balance=90,
            fan_token_lifetime_earned=90,
            level="新生儿",
            is_official_member=True,
        )
        session.add(profile)
        await session.flush()

        await fan_token_service.award(
            session,
            user_id=user.id,
            delta=20,
            source_type="test-reward",
            source_id="reward-3",
            idempotency_key=f"test-member-card-sync:{user.id}",
            description="Test automatic member card sync",
        )

        assert profile.level == "轻度神经"
        assert session.info[MEMBERSHIP_CARD_SYNC_KEY] == {user.id}
        await session.rollback()
