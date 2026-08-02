import base64
import io
from typing import cast

import pytest
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

import app.models.database  # noqa: F401
from app.adapters.monad import ConfirmedContractTransaction, monad_contract_adapter
from app.adapters.pinata import PinnedFile, pinata_adapter
from app.core.config import settings
from app.models.community import FanTask, TaskParticipation
from app.models.membership import MembershipLevel
from app.models.nft import (
    ChainOperation,
    CollectibleOwnership,
    CollectibleTokenType,
    MembershipIdentityNft,
    NftApplication,
    NftMetadataVersion,
    TaskNftReward,
)
from app.models.user import Community, User, UserProfile, Wallet
from app.services.identity import AuthenticatedIdentity
from app.services.fan_tokens import fan_token_service
from app.services.nft import NftService, NftValidationError


def image_data_url(width: int = 256, height: int = 256) -> str:
    stream = io.BytesIO()
    Image.new("RGB", (width, height), "purple").save(stream, format="PNG")
    encoded = base64.b64encode(stream.getvalue()).decode()
    return f"data:image/png;base64,{encoded}"


def test_custom_badge_image_validation_accepts_safe_png() -> None:
    content, mime_type, width, height = NftService._parse_image(image_data_url())
    assert content
    assert mime_type == "image/png"
    assert (width, height) == (256, 256)


def test_token_ids_remain_stable_after_local_gallery_data_is_cleared() -> None:
    fan_token_id = NftService._token_id("fan-nft", "creation-1")

    assert fan_token_id == NftService._token_id("fan-nft", "creation-1")
    assert fan_token_id != NftService._token_id("fan-nft", "creation-2")
    assert fan_token_id != NftService._token_id("task-reward", "creation-1")
    assert 0 < fan_token_id < 2**63


@pytest.mark.asyncio
async def test_fan_nft_can_be_purchased_repeatedly_by_the_same_wallet(monkeypatch) -> None:
    monkeypatch.setattr(settings, "chain_writes_enabled", True)
    monkeypatch.setattr(settings, "collectibles_contract_address", "0x" + "22" * 20)
    monkeypatch.setattr(settings, "collectible_type_manager_private_key", "0x" + "1" * 64)
    monkeypatch.setattr(settings, "collectible_minter_private_key", "0x" + "2" * 64)
    minted_claims: list[str] = []

    async def mint_collectible(_wallet: str, _token_id: int, _amount: int, claim_hash: str):
        minted_claims.append(claim_hash)
        return ConfirmedContractTransaction(
            transaction_hash="0x" + f"{len(minted_claims):064x}",
            block_number=len(minted_claims),
            confirmations=1,
            event_args={},
        )

    async def award(_session, **_kwargs):
        return None

    monkeypatch.setattr(monad_contract_adapter, "mint_collectible", mint_collectible)
    monkeypatch.setattr(fan_token_service, "award", award)
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
            creator = User(display_name="Creator")
            buyer = User(display_name="Repeat Buyer")
            session.add_all([creator, buyer])
            await session.flush()
            session.add_all([
                UserProfile(user_id=creator.id, is_official_member=True),
                UserProfile(user_id=buyer.id, is_official_member=True),
                Wallet(
                    user_id=buyer.id,
                    address="0x1111111111111111111111111111111111111111",
                    wallet_type="external",
                    is_primary=True,
                ),
            ])
            application = NftApplication(
                user_id=creator.id,
                name="Repeatable NFT",
                description="Repeatable development NFT",
                theme="repeat",
                copyright_declaration="Original development asset",
                price_fan_tokens=10,
                max_supply=10,
                image_mime_type="image/png",
                image_size_bytes=100,
                image_width=256,
                image_height=256,
                status="MINTED",
            )
            session.add(application)
            await session.flush()
            token_type = CollectibleTokenType(
                token_id=77,
                category="FAN_LIMITED_NFT",
                name=application.name,
                description=application.description,
                chain_id=settings.monad_chain_id,
                contract_address=settings.collectibles_contract_address,
                metadata_cid="repeatable-metadata",
                max_supply=10,
                minted_supply=1,
                per_wallet_limit=10,
                mint_start=application.created_at,
                mint_end=application.created_at,
                transferable=True,
                source_type="FAN_NFT",
                source_id=application.id,
                status="CONFIRMED",
            )
            session.add(token_type)
            await session.flush()
            application.collectible_token_type_id = token_type.id
            await session.commit()
            identity = AuthenticatedIdentity(
                user_id=buyer.id,
                primary_wallet="0x1111111111111111111111111111111111111111",
                wallet_type="external",
                provider="wallet",
            )

            first = await NftService().buy_fan_nft(session, identity, application)
            second = await NftService().buy_fan_nft(session, identity, application)

            assert first.id == second.id
            assert second.amount == 2
            assert token_type.minted_supply == 3
            assert len(minted_claims) == 2
            assert minted_claims[0] != minted_claims[1]
    finally:
        await engine.dispose()


def test_custom_badge_image_validation_rejects_small_images() -> None:
    with pytest.raises(NftValidationError, match="dimensions"):
        NftService._parse_image(image_data_url(64, 64))


@pytest.mark.asyncio
async def test_membership_card_renders_downloadable_png_with_qr_panel() -> None:
    service = NftService()
    level = MembershipLevel(
        code="mild-neuro",
        name="轻度神经",
        description="活跃会员",
        rank=2,
        min_token_balance=100,
        max_token_balance=499,
        badge_image_url="/img/badges/mild.png",
    )
    user = User(id="member-card-user", display_name="Fanora Member")
    profile = UserProfile(
        user_id=user.id,
        username="fanora_member",
        level=level.name,
        fan_token_balance=600,
        fan_token_lifetime_earned=1200,
        is_official_member=True,
    )
    record = MembershipIdentityNft(
        user_id=user.id,
        wallet_address="0x1111111111111111111111111111111111111111",
        chain_id=10143,
        contract_address="0x2222222222222222222222222222222222222222",
        token_id=9,
        level_id=level.rank,
        level_code=level.code,
        metadata_cid="metadata-cid",
    )

    content = await service._render_membership_card(
        user=user,
        profile=profile,
        level=level,
        record=record,
        version=2,
    )

    with Image.open(io.BytesIO(content)) as card:
        assert card.format == "PNG"
        assert card.size == (842, 1468)
        qr_area = card.crop((556, 982, 720, 1146)).convert("L")
        darkest, lightest = cast(tuple[int, int], qr_area.getextrema())
        assert darkest < 50
        assert lightest > 240


def test_membership_card_refresh_fingerprint_tracks_identity_copy_and_level() -> None:
    service = NftService()
    level = MembershipLevel(
        code="newborn",
        name="新生儿",
        description="新会员",
        rank=1,
        min_token_balance=0,
        max_token_balance=99,
        badge_image_url="/img/badges/new.png",
    )
    user = User(id="fingerprint-user", display_name="Member")
    profile = UserProfile(user_id=user.id, fan_token_lifetime_earned=10)
    record = MembershipIdentityNft(
        user_id=user.id,
        wallet_address="0x1111111111111111111111111111111111111111",
        chain_id=10143,
        contract_address="0x2222222222222222222222222222222222222222",
        token_id=1,
        level_id=1,
        level_code=level.code,
        metadata_cid="metadata-cid",
    )
    before = service.membership_card_content_hash(user=user, profile=profile, level=level, record=record)
    record.is_member_card = True
    record.card_level_code = level.code
    record.card_content_hash = before
    assert service.membership_card_needs_refresh(user=user, profile=profile, level=level, record=record) is False
    profile.fan_token_lifetime_earned = 500
    balance_only = service.membership_card_content_hash(user=user, profile=profile, level=level, record=record)
    assert before == balance_only
    user.display_name = "Renamed Member"
    renamed = service.membership_card_content_hash(user=user, profile=profile, level=level, record=record)
    assert before != renamed
    assert service.membership_card_needs_refresh(user=user, profile=profile, level=level, record=record) is True
    profile.username = "renamed_member"
    username_changed = service.membership_card_content_hash(user=user, profile=profile, level=level, record=record)
    assert renamed != username_changed
    upgraded = MembershipLevel(
        code="mild-neuro",
        name="轻度神经",
        description="活跃会员",
        rank=2,
        min_token_balance=100,
        max_token_balance=499,
        badge_image_url="/img/badges/mild.png",
    )
    upgraded_hash = service.membership_card_content_hash(user=user, profile=profile, level=upgraded, record=record)
    assert username_changed != upgraded_hash


@pytest.mark.asyncio
async def test_fear_task_reward_mints_once_with_local_concert_image(monkeypatch) -> None:
    chain_calls: list[str] = []

    async def pin_image(filename: str, content: bytes, mime_type: str) -> PinnedFile:
        assert filename.endswith(".webp")
        assert content
        assert mime_type == "image/webp"
        return PinnedFile(cid="fear-image-cid", pin_id="fear-image-pin")

    async def pin_metadata(filename: str, payload: dict) -> PinnedFile:
        assert filename.endswith(".json")
        assert payload["image"] == "ipfs://fear-image-cid"
        return PinnedFile(cid="fear-metadata-cid", pin_id="fear-metadata-pin")

    async def create_token_type(payload: dict) -> ConfirmedContractTransaction:
        chain_calls.append("create")
        assert payload["category"] == 0
        return ConfirmedContractTransaction(
            transaction_hash="0x" + "11" * 32,
            block_number=100,
            confirmations=1,
            event_args={},
        )

    async def mint_collectible(wallet: str, token_id: int, amount: int, claim_hash: str):
        chain_calls.append("mint")
        assert wallet == "0x1111111111111111111111111111111111111111"
        assert amount == 1
        assert token_id > 0
        assert len(claim_hash.removeprefix("0x")) == 64
        return ConfirmedContractTransaction(
            transaction_hash="0x" + "22" * 32,
            block_number=101,
            confirmations=1,
            event_args={},
        )

    monkeypatch.setattr(settings, "chain_writes_enabled", True)
    monkeypatch.setattr(settings, "pinata_jwt", "test-pinata-jwt")
    monkeypatch.setattr(settings, "collectibles_contract_address", "0x2222222222222222222222222222222222222222")
    monkeypatch.setattr(settings, "collectible_type_manager_private_key", "0x" + "1" * 64)
    monkeypatch.setattr(settings, "collectible_minter_private_key", "0x" + "2" * 64)
    monkeypatch.setattr(pinata_adapter, "pin_image", pin_image)
    monkeypatch.setattr(pinata_adapter, "pin_metadata", pin_metadata)
    monkeypatch.setattr(monad_contract_adapter, "create_token_type", create_token_type)
    monkeypatch.setattr(monad_contract_adapter, "mint_collectible", mint_collectible)

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
            user = User(display_name="Fear Ticket Fan")
            session.add(user)
            await session.flush()
            community = Community(
                owner_user_id=user.id,
                slug="fear-ticket-test",
                name="Fear Ticket Test",
                description="Task reward test community",
                logo_url="/img/logo.png",
            )
            session.add_all(
                [
                    UserProfile(user_id=user.id, is_official_member=True),
                    Wallet(
                        user_id=user.id,
                        address="0x1111111111111111111111111111111111111111",
                        wallet_type="external",
                        is_primary=True,
                    ),
                    community,
                ]
            )
            await session.flush()
            task = FanTask(
                community_id=community.id,
                created_by_user_id=user.id,
                title="FEAR and DREAMS 纪念票任务",
                description="分享真实现场记忆并领取纪念票",
                task_type="page_action",
                status="published",
                reward_fan_tokens=500,
                validation_rule={
                    "nft_reward": {
                        "enabled": True,
                        "version": 1,
                        "category": "CONCERT_CARD",
                        "name": "FEAR and DREAMS 纪念票",
                        "image_path": "/img/fanora/eason-concert.webp",
                        "max_supply": 10000,
                        "per_wallet_limit": 1,
                        "transferable": False,
                    }
                },
            )
            session.add(task)
            await session.flush()
            participation = TaskParticipation(
                task_id=task.id,
                user_id=user.id,
                status="rewarded",
                reward_snapshot=500,
            )
            session.add(participation)
            await session.commit()

            service = NftService()
            first = await service.mint_task_reward(
                session,
                task=task,
                participation=participation,
                user_id=user.id,
            )
            second = await service.mint_task_reward(
                session,
                task=task,
                participation=participation,
                user_id=user.id,
            )

            assert first is not None and first.status == "CONFIRMED"
            assert second is not None and second.id == first.id
            assert chain_calls == ["create", "mint"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_task_reward_pinata_failure_returns_retryable_without_missing_greenlet(monkeypatch) -> None:
    async def pin_image(filename: str, content: bytes, mime_type: str) -> PinnedFile:
        raise RuntimeError("Pinata upload failed after bounded retries")

    monkeypatch.setattr(settings, "chain_writes_enabled", True)
    monkeypatch.setattr(settings, "pinata_jwt", "test-pinata-jwt")
    monkeypatch.setattr(settings, "collectibles_contract_address", "0x2222222222222222222222222222222222222222")
    monkeypatch.setattr(settings, "collectible_type_manager_private_key", "0x" + "1" * 64)
    monkeypatch.setattr(settings, "collectible_minter_private_key", "0x" + "2" * 64)
    monkeypatch.setattr(pinata_adapter, "pin_image", pin_image)

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
            user = User(display_name="Retryable Reward Fan")
            session.add(user)
            await session.flush()
            community = Community(
                owner_user_id=user.id,
                slug="retryable-reward-test",
                name="Retryable Reward Test",
                description="Task reward retry test community",
                logo_url="/img/logo.png",
            )
            session.add_all(
                [
                    UserProfile(user_id=user.id, is_official_member=True),
                    Wallet(
                        user_id=user.id,
                        address="0x1111111111111111111111111111111111111111",
                        wallet_type="external",
                        is_primary=True,
                    ),
                    community,
                ]
            )
            await session.flush()
            task = FanTask(
                community_id=community.id,
                created_by_user_id=user.id,
                title="FEAR and DREAMS 纪念票任务",
                description="分享真实现场记忆并领取纪念票",
                task_type="page_action",
                status="published",
                reward_fan_tokens=500,
                validation_rule={
                    "nft_reward": {
                        "enabled": True,
                        "version": 1,
                        "category": "CONCERT_CARD",
                        "name": "FEAR and DREAMS 纪念票",
                        "image_path": "/img/fanora/eason-concert.webp",
                        "max_supply": 10000,
                        "per_wallet_limit": 1,
                        "transferable": False,
                    }
                },
            )
            session.add(task)
            await session.flush()
            participation = TaskParticipation(
                task_id=task.id,
                user_id=user.id,
                status="rewarded",
                reward_snapshot=500,
            )
            session.add(participation)
            await session.commit()

            reward = await NftService().mint_task_reward(
                session,
                task=task,
                participation=participation,
                user_id=user.id,
            )

            assert reward is not None
            assert reward.status == "RETRYABLE"
            assert reward.failure_reason == "Pinata upload failed after bounded retries"
            persisted = await session.get(TaskNftReward, reward.id)
            assert persisted is not None
            assert persisted.status == "RETRYABLE"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_owned_collectible_can_be_used_as_avatar_but_unowned_collectible_cannot() -> None:
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
            owner = User(display_name="NFT Owner")
            stranger = User(display_name="NFT Stranger")
            session.add_all([owner, stranger])
            await session.flush()
            owner_profile = UserProfile(user_id=owner.id)
            stranger_profile = UserProfile(user_id=stranger.id)
            token_type = CollectibleTokenType(
                token_id=7,
                category="FAN_LIMITED",
                name="Avatar NFT",
                description="Owned avatar NFT",
                chain_id=10143,
                contract_address="0x2222222222222222222222222222222222222222",
                metadata_cid="avatar-metadata-cid",
                max_supply=100,
                minted_supply=1,
                per_wallet_limit=1,
                mint_start=owner.created_at,
                mint_end=owner.created_at,
                source_type="FAN_NFT",
                source_id="avatar-creation",
                status="CONFIRMED",
            )
            session.add_all([owner_profile, stranger_profile, token_type])
            await session.flush()
            session.add_all(
                [
                    NftMetadataVersion(
                        subject_type="FAN_NFT",
                        subject_id="avatar-creation",
                        version=1,
                        image_cid="avatar-image-cid",
                        metadata_cid=token_type.metadata_cid,
                        content_hash="a" * 64,
                        size_bytes=128,
                        mime_type="image/png",
                    ),
                    CollectibleOwnership(
                        token_type_id=token_type.id,
                        user_id=owner.id,
                        wallet_address="0x1111111111111111111111111111111111111111",
                        amount=1,
                        claim_key="0x" + "1" * 64,
                        status="CONFIRMED",
                    ),
                ]
            )
            await session.commit()

            avatar_url = await NftService().set_collectible_avatar(
                session,
                AuthenticatedIdentity(
                    user_id=owner.id,
                    primary_wallet="0x1111111111111111111111111111111111111111",
                    wallet_type="external",
                    provider="wallet",
                ),
                token_type.id,
            )
            assert avatar_url == pinata_adapter.gateway_url("avatar-image-cid")
            assert owner_profile.avatar_url == avatar_url

            with pytest.raises(NftValidationError, match="confirmed owned NFT"):
                await NftService().set_collectible_avatar(
                    session,
                    AuthenticatedIdentity(
                        user_id=stranger.id,
                        primary_wallet="0x3333333333333333333333333333333333333333",
                        wallet_type="external",
                        provider="wallet",
                    ),
                    token_type.id,
                )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_membership_levels_pin_their_own_badge_images(monkeypatch) -> None:
    pinned_names: list[str] = []

    async def pin_image(filename: str, content: bytes, mime_type: str) -> PinnedFile:
        assert content
        assert mime_type == "image/png"
        pinned_names.append(filename)
        return PinnedFile(cid=f"cid-{filename}", pin_id=f"pin-{filename}")

    monkeypatch.setattr(pinata_adapter, "pin_image", pin_image)
    service = NftService()
    newborn = MembershipLevel(
        code="newborn",
        name="新生儿",
        description="新会员",
        rank=1,
        min_token_balance=0,
        max_token_balance=99,
        badge_image_url="/img/badges/new.png",
    )
    mild = MembershipLevel(
        code="mild-neuro",
        name="轻度神经",
        description="活跃会员",
        rank=2,
        min_token_balance=100,
        max_token_balance=499,
        badge_image_url="/img/badges/mild.png",
    )

    newborn_cid = await service._pin_membership_level_image(newborn)
    mild_cid = await service._pin_membership_level_image(mild)

    assert newborn_cid != mild_cid
    assert newborn.badge_image_cid == "cid-membership-level-newborn"
    assert mild.badge_image_cid == "cid-membership-level-mild-neuro"
    assert pinned_names == ["membership-level-newborn", "membership-level-mild-neuro"]


@pytest.mark.asyncio
async def test_retryable_membership_identity_mint_reuses_the_original_operation(monkeypatch) -> None:
    calls: list[tuple[str, int, str, str]] = []

    async def mint_identity(
        wallet: str, level_id: int, metadata_uri: str, operation_hash: str
    ) -> ConfirmedContractTransaction:
        calls.append((wallet, level_id, metadata_uri, operation_hash))
        return ConfirmedContractTransaction(
            transaction_hash="0x" + "ab" * 32,
            block_number=321,
            confirmations=1,
            event_args={"tokenId": 7},
        )

    class FakeSession:
        commits = 0

        async def commit(self) -> None:
            self.commits += 1

    monkeypatch.setattr(monad_contract_adapter, "mint_identity", mint_identity)
    identity = AuthenticatedIdentity(
        user_id="user-1",
        primary_wallet="0x1111111111111111111111111111111111111111",
        wallet_type="external",
        provider="rainbowkit",
    )
    operation = ChainOperation(
        operation_type="IDENTITY_MINT",
        idempotency_key="identity-mint:user-1",
        operation_hash="0x" + "12" * 32,
        chain_id=10143,
        contract_address="0x2222222222222222222222222222222222222222",
        status="RETRYABLE",
    )
    record = MembershipIdentityNft(
        user_id=identity.user_id,
        wallet_address=identity.primary_wallet,
        chain_id=10143,
        contract_address=operation.contract_address,
        level_id=1,
        level_code="newborn",
        metadata_cid="metadata-cid",
        chain_operation_id=operation.id,
        status="RETRYABLE",
    )

    result = await NftService()._submit_membership_identity_mint(
        FakeSession(),  # type: ignore[arg-type]
        identity,
        record,
        operation,
        is_retry=True,
    )

    assert calls == [(identity.primary_wallet, 1, "ipfs://metadata-cid", operation.operation_hash)]
    assert operation.retry_count == 1
    assert operation.status == "CONFIRMED"
    assert result.status == "CONFIRMED"
    assert result.token_id == 7
