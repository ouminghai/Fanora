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
from app.models.membership import MembershipLevel
from app.models.nft import (
    ChainOperation,
    CollectibleOwnership,
    CollectibleTokenType,
    MembershipIdentityNft,
    NftMetadataVersion,
)
from app.models.user import User, UserProfile
from app.services.identity import AuthenticatedIdentity
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


def test_membership_card_refresh_fingerprint_tracks_lifetime_level_data() -> None:
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
    profile.fan_token_lifetime_earned = 500
    after = service.membership_card_content_hash(user=user, profile=profile, level=level, record=record)
    assert before != after


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
        code="newborn", name="新生儿", description="新会员", rank=1,
        min_token_balance=0, max_token_balance=99, badge_image_url="/img/badges/new.png",
    )
    mild = MembershipLevel(
        code="mild-neuro", name="轻度神经", description="活跃会员", rank=2,
        min_token_balance=100, max_token_balance=499, badge_image_url="/img/badges/mild.png",
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
