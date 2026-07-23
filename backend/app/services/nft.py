"""NFT orchestration across deterministic rules, Pinata, PostgreSQL, and Monad."""

import base64
import hashlib
import io
import json
import mimetypes
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import httpx
import qrcode
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, UnidentifiedImageError
from qrcode.constants import ERROR_CORRECT_Q
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from app.adapters.monad import ChainConfigurationError, monad_contract_adapter
from app.adapters.pinata import pinata_adapter
from app.core.config import settings
from app.core.logging import logger
from app.models.base import utc_now
from app.models.membership import MembershipLevel
from app.models.nft import (
    ChainOperation,
    CollectibleOwnership,
    CollectibleTokenType,
    MembershipIdentityNft,
    NftApplication,
    NftMetadataVersion,
)
from app.models.user import User, UserProfile, Wallet
from app.schemas.nft import NftApplicationCreate
from app.services.fan_tokens import fan_token_service
from app.services.identity import AuthenticatedIdentity

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class NftValidationError(ValueError):
    pass


def _explorer(address: str, token_id: int | None = None) -> str:
    suffix = f"?a={token_id}" if token_id is not None else ""
    return f"https://testnet.monadexplorer.com/address/{address}{suffix}"


class NftService:
    @staticmethod
    def _parse_image(data_url: str) -> tuple[bytes, str, int, int]:
        header, encoded = data_url.split(",", 1)
        mime_type = header[5:].split(";", 1)[0].lower()
        if mime_type not in ALLOWED_IMAGE_TYPES:
            raise NftValidationError("Only JPEG, PNG, WebP, and GIF images are supported")
        try:
            content = base64.b64decode(encoded, validate=True)
        except ValueError as error:
            raise NftValidationError("Image data is not valid base64") from error
        if not content or len(content) > settings.nft_max_image_bytes:
            raise NftValidationError("Image exceeds the configured file size limit")
        try:
            with Image.open(io.BytesIO(content)) as image:
                image.verify()
            with Image.open(io.BytesIO(content)) as image:
                width, height = image.size
        except (UnidentifiedImageError, OSError) as error:
            raise NftValidationError("Uploaded file is not a valid image") from error
        minimum, maximum = settings.nft_min_image_dimension, settings.nft_max_image_dimension
        if width < minimum or height < minimum or width > maximum or height > maximum:
            raise NftValidationError(f"Image dimensions must be between {minimum} and {maximum} pixels")
        return content, mime_type, width, height

    async def _membership_level_image_bytes(self, level: MembershipLevel) -> tuple[bytes, str]:
        source = level.badge_image_url.strip()
        if source.startswith("ipfs://"):
            source = pinata_adapter.gateway_url(source.removeprefix("ipfs://"))
        if source.startswith("data:image/"):
            content, mime_type, _, _ = self._parse_image(source)
        elif source.startswith(("http://", "https://")):
            async with httpx.AsyncClient(timeout=settings.pinata_timeout_seconds) as client:
                response = await client.get(source)
                response.raise_for_status()
                content = response.content
                mime_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        else:
            public_root = Path(__file__).resolve().parents[3] / "frontend" / "public"
            path = (public_root / source.lstrip("/")).resolve()
            if not path.is_relative_to(public_root.resolve()) or not path.is_file():
                raise NftValidationError(f"Membership level image does not exist: {source}")
            content = path.read_bytes()
            mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if mime_type not in ALLOWED_IMAGE_TYPES:
            raise NftValidationError("Membership level image must be JPEG, PNG, or WebP")
        if not content or len(content) > settings.nft_max_image_bytes:
            raise NftValidationError("Membership level image exceeds the configured size limit")
        return content, mime_type

    async def _pin_membership_level_image(self, level: MembershipLevel) -> str:
        if level.badge_image_cid:
            return level.badge_image_cid
        content, mime_type = await self._membership_level_image_bytes(level)
        content_hash = hashlib.sha256(content).hexdigest()
        pinned = await pinata_adapter.pin_image(f"membership-level-{level.code}", content, mime_type)
        level.badge_image_cid = pinned.cid
        level.badge_image_pin_id = pinned.pin_id
        level.badge_image_content_hash = content_hash
        return pinned.cid

    @staticmethod
    def _member_card_font(size: int, *, display: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        public_fonts = Path(__file__).resolve().parents[3] / "frontend" / "public" / "fonts"
        candidates = (
            [public_fonts / "CalSans-SemiBold.ttf"]
            if display
            else [
                Path("/System/Library/Fonts/PingFang.ttc"),
                Path("/System/Library/Fonts/Supplemental/Songti.ttc"),
                Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
                public_fonts / "DM_Sans" / "DMSans-Medium.ttf",
            ]
        )
        for path in candidates:
            if path.is_file():
                return ImageFont.truetype(str(path), size=size)
        return ImageFont.load_default(size=size)

    @staticmethod
    def _short_card_value(value: str, head: int = 7, tail: int = 5) -> str:
        return value if len(value) <= head + tail + 3 else f"{value[:head]}...{value[-tail:]}"

    def membership_card_content_hash(
        self,
        *,
        user: User,
        profile: UserProfile,
        level: MembershipLevel,
        record: MembershipIdentityNft,
    ) -> str:
        payload = {
            "card_design_version": 3,
            "display_name": user.display_name or profile.username or "Fanora Member",
            "username": profile.username or "",
            "level_code": level.code,
            "level_name": level.name,
            "lifetime_fan": profile.fan_token_lifetime_earned,
            "wallet": record.wallet_address.lower(),
            "contract": record.contract_address.lower(),
            "token_id": record.token_id,
            "joined_at": profile.official_member_since.isoformat() if profile.official_member_since else "",
        }
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    async def _render_membership_card(
        self,
        *,
        user: User,
        profile: UserProfile,
        level: MembershipLevel,
        record: MembershipIdentityNft,
        version: int,
    ) -> bytes:
        if record.token_id is None:
            raise NftValidationError("Membership identity token is not confirmed")
        public_root = Path(__file__).resolve().parents[3] / "frontend" / "public"
        template_path = public_root / "img" / "membercard" / "membercard.jpg"
        if not template_path.is_file():
            raise NftValidationError("Membership card template is unavailable")

        scale = 2
        with Image.open(template_path) as source:
            card = source.convert("RGB").resize((source.width * scale, source.height * scale), Image.Resampling.LANCZOS)
        badge_bytes, _ = await self._membership_level_image_bytes(level)
        with Image.open(io.BytesIO(badge_bytes)) as source_badge:
            badge = source_badge.convert("RGBA")
        badge.thumbnail((238 * scale, 270 * scale), Image.Resampling.LANCZOS)
        badge_x = (card.width - badge.width) // 2
        badge_y = 100 * scale + max((255 * scale - badge.height) // 2, 0)
        shadow = Image.new("RGBA", card.size, (0, 0, 0, 0))
        shadow_alpha = badge.getchannel("A").filter(ImageFilter.GaussianBlur(12 * scale))
        shadow_layer = Image.new("RGBA", badge.size, (20, 44, 91, 95))
        shadow_layer.putalpha(shadow_alpha)
        shadow.alpha_composite(shadow_layer, (badge_x, badge_y + 7 * scale))
        card = Image.alpha_composite(card.convert("RGBA"), shadow)
        card.alpha_composite(badge, (badge_x, badge_y))

        draw = ImageDraw.Draw(card)
        dark = (25, 38, 63, 255)
        muted = (75, 89, 112, 255)
        cyan = (22, 139, 184, 255)
        display_name = user.display_name or profile.username or "Fanora Member"
        username = display_name
        explorer_url = (
            f"https://testnet.monadvision.com/nft/{record.contract_address}/{record.token_id}?tab=Overview"
        )
        title_font = self._member_card_font(10 * scale, display=True)
        name_font = self._member_card_font(17 * scale)
        username_font = self._member_card_font(20 * scale)
        detail_font = self._member_card_font(8 * scale)
        small_font = self._member_card_font(7 * scale)
        username_x = card.width // 2
        username_y = 400 * scale
        draw.text(
            (username_x, username_y),
            username[:30],
            font=username_font,
            fill=dark,
            anchor="mm",
        )
        left = 66 * scale
        draw.text((left, 470 * scale), "FANORA MEMBER ID", font=title_font, fill=cyan)
        draw.text((left, 488 * scale), display_name[:24], font=name_font, fill=dark)
        level_label = f"{level.name}  ·  LEVEL {level.rank}"
        draw.rounded_rectangle(
            (left, 516 * scale, 250 * scale, 535 * scale),
            radius=8 * scale,
            fill=(229, 240, 246, 230),
        )
        draw.text((left + 8 * scale, 520 * scale), level_label, font=detail_font, fill=(31, 97, 126, 255))
        draw.text(
            (left, 543 * scale),
            f"TOKEN #{record.token_id}   ·   META V{version}",
            font=detail_font,
            fill=dark,
        )
        draw.text(
            (left, 558 * scale),
            f"WALLET  {self._short_card_value(record.wallet_address)}",
            font=small_font,
            fill=muted,
        )
        draw.text(
            (left, 572 * scale),
            f"CONTRACT  {self._short_card_value(record.contract_address)}",
            font=small_font,
            fill=muted,
        )
        draw.text(
            (left, 586 * scale),
            f"LIFETIME FAN  {profile.fan_token_lifetime_earned:,}",
            font=small_font,
            fill=muted,
        )

        qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_Q, box_size=5, border=3)
        qr.add_data(explorer_url)
        qr.make(fit=True)
        qr_image = cast(Any, qr.make_image(fill_color="#15263f", back_color="white")).convert("RGB")
        qr_image = ImageOps.contain(qr_image, (82 * scale, 82 * scale), Image.Resampling.NEAREST)
        qr_x, qr_y = 278 * scale, 504 * scale
        card.alpha_composite(qr_image.convert("RGBA"), (qr_x, qr_y))
        draw.text((291 * scale, 592 * scale), "SCAN ON MONAD", font=small_font, fill=muted)

        fanora_logo_path = public_root / "img" / "logo.png"
        if not fanora_logo_path.is_file():
            raise NftValidationError("Membership card brand assets are unavailable")
        with Image.open(fanora_logo_path) as source_logo:
            fanora_logo = ImageOps.contain(
                source_logo.convert("RGBA"),
                (190 * scale, 53 * scale),
                Image.Resampling.LANCZOS,
            )
        card.alpha_composite(
            fanora_logo,
            (
                (card.width - fanora_logo.width) // 2,
                633 * scale,
            ),
        )

        stream = io.BytesIO()
        card.convert("RGB").save(stream, format="PNG", optimize=True)
        return stream.getvalue()

    async def _pin_membership_card_metadata(
        self,
        *,
        identity: AuthenticatedIdentity,
        user: User,
        profile: UserProfile,
        level: MembershipLevel,
        record: MembershipIdentityNft,
        version: int,
    ) -> tuple[NftMetadataVersion, str, str]:
        card_bytes = await self._render_membership_card(
            user=user,
            profile=profile,
            level=level,
            record=record,
            version=version,
        )
        card_hash = self.membership_card_content_hash(user=user, profile=profile, level=level, record=record)
        image = await pinata_adapter.pin_image(
            f"fanora-member-card-{identity.user_id}-v{version}.png",
            card_bytes,
            "image/png",
        )
        explorer_url = (
            f"https://testnet.monadvision.com/nft/{record.contract_address}/{record.token_id}?tab=Overview"
        )
        metadata = {
            "name": f"Fanora Member Card · {level.name}",
            "description": "A downloadable, soulbound Fanora membership card that proves the holder's fandom identity.",
            "image": pinata_adapter.ipfs_uri(image.cid),
            "external_url": explorer_url,
            "issuer": settings.fanora_issuer_name,
            "identity_card": {
                "downloadable": True,
                "soulbound": True,
                "card_version": version,
            },
            "attributes": [
                {"trait_type": "Membership Level", "value": level.name},
                {"trait_type": "Level Code", "value": level.code},
                {"trait_type": "Level ID", "value": str(level.rank)},
                {"trait_type": "Lifetime FAN", "value": str(profile.fan_token_lifetime_earned)},
                {"trait_type": "Identity Token", "value": str(record.token_id)},
                {"trait_type": "Metadata Version", "value": str(version)},
                {"trait_type": "Soulbound", "value": "true"},
            ],
        }
        pinned = await pinata_adapter.pin_metadata(
            f"fanora-member-card-{identity.user_id}-v{version}.json",
            metadata,
        )
        metadata_version = NftMetadataVersion(
            subject_type="MEMBERSHIP_IDENTITY",
            subject_id=identity.user_id,
            version=version,
            image_cid=image.cid,
            image_pin_id=image.pin_id,
            metadata_cid=pinned.cid,
            metadata_pin_id=pinned.pin_id,
            content_hash=hashlib.sha256(card_bytes).hexdigest(),
            size_bytes=len(card_bytes),
            mime_type="image/png",
            metadata_payload=metadata,
            created_by_user_id=identity.user_id,
        )
        return metadata_version, pinned.cid, card_hash

    async def _pin_membership_metadata(
        self,
        *,
        identity: AuthenticatedIdentity,
        profile: UserProfile,
        level: MembershipLevel,
        version: int,
    ) -> tuple[NftMetadataVersion, str]:
        image_cid = await self._pin_membership_level_image(level)
        metadata = {
            "name": f"Fanora Membership · {level.name}",
            "description": level.description,
            "image": pinata_adapter.ipfs_uri(image_cid),
            "external_url": "https://fanora.xyz",
            "issuer": settings.fanora_issuer_name,
            "proof_of_fandom": {
                "summary": f"Verified Fanora member at {level.name} level.",
                "version": version,
            },
            "attributes": [
                {"trait_type": "Membership Level", "value": level.name},
                {"trait_type": "Level Code", "value": level.code},
                {"trait_type": "Level ID", "value": str(level.rank)},
                {
                    "trait_type": "Joined At",
                    "value": profile.official_member_since.isoformat() if profile.official_member_since else "",
                },
                {"trait_type": "Metadata Version", "value": str(version)},
                {"trait_type": "Soulbound", "value": "true"},
            ],
        }
        metadata_bytes = json.dumps(metadata, ensure_ascii=False, sort_keys=True).encode("utf-8")
        pinned = await pinata_adapter.pin_metadata(
            f"fanora-identity-{identity.user_id}-v{version}.json", metadata
        )
        record = NftMetadataVersion(
            subject_type="MEMBERSHIP_IDENTITY",
            subject_id=identity.user_id,
            version=version,
            image_cid=image_cid,
            image_pin_id=level.badge_image_pin_id,
            metadata_cid=pinned.cid,
            metadata_pin_id=pinned.pin_id,
            content_hash=hashlib.sha256(metadata_bytes).hexdigest(),
            size_bytes=len(metadata_bytes),
            mime_type="application/json",
            metadata_payload=metadata,
            created_by_user_id=identity.user_id,
        )
        return record, pinned.cid

    async def _identity_level_for_profile(
        self,
        session: AsyncSession,
        profile: UserProfile,
    ) -> MembershipLevel | None:
        current_level = (
            await session.execute(select(MembershipLevel).where(MembershipLevel.name == profile.level))
        ).scalar_one_or_none()
        if current_level is not None and current_level.is_management:
            return current_level
        return (
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

    async def create_application(
        self, session: AsyncSession, identity: AuthenticatedIdentity, payload: NftApplicationCreate
    ) -> NftApplication:
        content, mime_type, width, height = self._parse_image(payload.image_data_url)
        application = NftApplication(
            user_id=identity.user_id,
            name=payload.name.strip(),
            description=payload.description.strip(),
            story_image_urls=[],
            theme=payload.theme.strip(),
            price_fan_tokens=payload.price_fan_tokens,
            max_supply=payload.max_supply,
            publish_fee_fan_tokens=settings.nft_publish_fee_fan_tokens,
            public_attributes=[item.model_dump() for item in payload.public_attributes],
            copyright_declaration=payload.copyright_declaration.strip(),
            image_data=payload.image_data_url,
            image_mime_type=mime_type,
            image_size_bytes=len(content),
            image_width=width,
            image_height=height,
        )
        session.add(application)
        await session.commit()
        await session.refresh(application)
        return application

    async def publish_fan_nft(
        self, session: AsyncSession, identity: AuthenticatedIdentity, payload: NftApplicationCreate
    ) -> NftApplication:
        profile = await session.get(UserProfile, identity.user_id, with_for_update=True)
        if profile is None:
            raise NftValidationError("User profile is required")
        user = await session.get(User, identity.user_id)
        creator_name = (user.display_name if user else None) or profile.username or identity.primary_wallet[:8]
        if profile.fan_token_balance < settings.nft_publish_fee_fan_tokens:
            raise NftValidationError(
                f"Publishing a fan NFT requires {settings.nft_publish_fee_fan_tokens} FAN"
            )
        if payload.price_fan_tokens < settings.nft_min_price_fan_tokens:
            raise NftValidationError("NFT price is below the configured minimum")
        if payload.price_fan_tokens > settings.nft_max_price_fan_tokens:
            raise NftValidationError("NFT price exceeds the configured maximum")
        if payload.max_supply < settings.nft_min_supply or payload.max_supply > settings.nft_max_supply:
            raise NftValidationError(
                f"NFT supply must be between {settings.nft_min_supply} and {settings.nft_max_supply}"
            )
        if not pinata_adapter.configured or not monad_contract_adapter.collectibles_configured:
            raise ChainConfigurationError("Pinata and collectible operator configuration are required")

        application = await self.create_application(session, identity, payload)
        application.status = "PINNING"
        application.submitted_at = utc_now()
        await session.commit()
        try:
            content, mime_type, _, _ = self._parse_image(payload.image_data_url)
            image = await pinata_adapter.pin_image(f"fan-nft-{application.id}", content, mime_type)
            application.story_image_urls = payload.story_image_urls
            metadata_payload = {
                "name": f"{creator_name} · {application.name}",
                "description": application.description,
                "image": pinata_adapter.ipfs_uri(image.cid),
                "category": "FAN_LIMITED_NFT",
                "issuer": settings.fanora_issuer_name,
                "theme": application.theme,
                "attributes": application.public_attributes
                + [
                    {"trait_type": "Category", "value": "FAN_LIMITED_NFT"},
                    {"trait_type": "Max Supply", "value": str(application.max_supply)},
                    {"trait_type": "Price FAN", "value": str(application.price_fan_tokens)},
                ],
            }
            metadata = await pinata_adapter.pin_metadata(f"fan-nft-{application.id}-v1.json", metadata_payload)
            version = NftMetadataVersion(
                subject_type="FAN_LIMITED_NFT",
                subject_id=application.id,
                version=1,
                image_cid=image.cid,
                image_pin_id=image.pin_id,
                metadata_cid=metadata.cid,
                metadata_pin_id=metadata.pin_id,
                content_hash=hashlib.sha256(content).hexdigest(),
                size_bytes=len(content),
                mime_type=mime_type,
                metadata_payload=metadata_payload,
                created_by_user_id=identity.user_id,
            )
            max_token_id = (
                await session.execute(select(func.max(CollectibleTokenType.token_id)))
            ).scalar_one_or_none() or 0
            token_id = int(max_token_id) + 1
            now = datetime.now(UTC)
            token_type = CollectibleTokenType(
                token_id=token_id,
                category="FAN_LIMITED_NFT",
                name=application.name,
                description=application.description,
                chain_id=settings.monad_chain_id,
                contract_address=settings.collectibles_contract_address.lower(),
                metadata_cid=metadata.cid,
                max_supply=application.max_supply,
                per_wallet_limit=1,
                mint_start=now - timedelta(minutes=1),
                mint_end=now + timedelta(days=3650),
                transferable=True,
                source_type="FAN_NFT",
                source_id=application.id,
            )
            create_key = f"fan-nft-type-create:{application.id}:v1"
            create_operation = ChainOperation(
                user_id=identity.user_id,
                operation_type="FAN_NFT_TYPE_CREATE",
                idempotency_key=create_key,
                operation_hash=monad_contract_adapter.operation_hash(create_key),
                chain_id=settings.monad_chain_id,
                contract_address=settings.collectibles_contract_address.lower(),
                token_id=token_id,
                metadata_cid=metadata.cid,
                request_payload={
                    "category": "FAN_LIMITED_NFT",
                    "max_supply": application.max_supply,
                    "price_fan_tokens": application.price_fan_tokens,
                },
            )
            session.add(version)
            session.add(token_type)
            session.add(create_operation)
            await session.flush()
            application.metadata_version_id = version.id
            application.collectible_token_type_id = token_type.id
            application.status = "MINTING"
            await session.commit()

            create_operation.status = "SUBMITTED"
            await session.commit()
            receipt = await monad_contract_adapter.create_token_type(
                {
                    "token_id": token_id,
                    "category": 3,
                    "metadata_uri": pinata_adapter.ipfs_uri(metadata.cid),
                    "max_supply": application.max_supply,
                    "per_wallet_limit": 1,
                    "mint_start": int(token_type.mint_start.timestamp()),
                    "mint_end": int(token_type.mint_end.timestamp()),
                    "transferable": True,
                }
            )
            create_operation.status = "CONFIRMED"
            create_operation.transaction_hash = receipt.transaction_hash
            create_operation.block_number = receipt.block_number
            create_operation.confirmations = receipt.confirmations
            create_operation.confirmed_at = utc_now()
            token_type.status = "CONFIRMED"

            creator_claim_key = f"fan-nft-creator-mint:{application.id}:v1"
            creator_claim_hash = monad_contract_adapter.operation_hash(creator_claim_key)
            creator_mint_operation = ChainOperation(
                user_id=identity.user_id,
                operation_type="FAN_NFT_CREATOR_MINT",
                idempotency_key=creator_claim_key,
                operation_hash=creator_claim_hash,
                chain_id=settings.monad_chain_id,
                contract_address=settings.collectibles_contract_address.lower(),
                token_id=token_id,
                metadata_cid=metadata.cid,
                request_payload={"wallet": identity.primary_wallet, "amount": 1},
            )
            session.add(creator_mint_operation)
            await session.flush()
            creator_ownership = CollectibleOwnership(
                token_type_id=token_type.id,
                user_id=identity.user_id,
                wallet_address=identity.primary_wallet,
                amount=0,
                claim_key=creator_claim_hash,
                chain_operation_id=creator_mint_operation.id,
            )
            session.add(creator_ownership)
            await session.commit()

            creator_mint_operation.status = "SUBMITTED"
            await session.commit()
            mint_receipt = await monad_contract_adapter.mint_collectible(
                identity.primary_wallet,
                token_id,
                1,
                creator_claim_hash,
            )
            creator_mint_operation.status = "CONFIRMED"
            creator_mint_operation.transaction_hash = mint_receipt.transaction_hash
            creator_mint_operation.block_number = mint_receipt.block_number
            creator_mint_operation.confirmations = mint_receipt.confirmations
            creator_mint_operation.confirmed_at = utc_now()
            creator_ownership.amount = 1
            creator_ownership.status = "CONFIRMED"
            creator_ownership.minted_at = utc_now()
            token_type.minted_supply = 1
            application.status = "MINTED"
            application.image_data = None
            await fan_token_service.award(
                session,
                user_id=identity.user_id,
                delta=-settings.nft_publish_fee_fan_tokens,
                source_type="fan-nft-publish",
                source_id=application.id,
                idempotency_key=f"fan-nft-publish-fee:{application.id}",
                description=f"发布限量 NFT：{application.name}",
            )
            await session.commit()
            return application
        except Exception:
            application_id = application.id
            await session.rollback()
            failed_application = await session.get(NftApplication, application_id)
            if failed_application is not None:
                failed_application.status = "FAILED"
                failed_application.updated_at = utc_now()
                await session.commit()
            logger.exception("fan_nft_publish_pipeline_failed", user_id=identity.user_id, application_id=application_id)
            raise

    async def buy_fan_nft(
        self, session: AsyncSession, identity: AuthenticatedIdentity, application: NftApplication
    ) -> CollectibleOwnership:
        if application.status != "MINTED" or not application.collectible_token_type_id:
            raise NftValidationError("NFT is not available for purchase")
        if application.user_id == identity.user_id:
            raise NftValidationError("You already own the creator side of this NFT")
        token_type = await session.get(CollectibleTokenType, application.collectible_token_type_id, with_for_update=True)
        if token_type is None or token_type.status != "CONFIRMED":
            raise NftValidationError("NFT token type is not confirmed")
        if token_type.minted_supply >= token_type.max_supply:
            raise NftValidationError("NFT is sold out")
        existing = (
            await session.execute(
                select(CollectibleOwnership).where(
                    CollectibleOwnership.token_type_id == token_type.id,
                    CollectibleOwnership.user_id == identity.user_id,
                )
            )
        ).scalar_one_or_none()
        if existing is not None and existing.amount > 0:
            raise NftValidationError("You already own this NFT")
        wallet = (
            await session.execute(
                select(Wallet.address).where(
                    Wallet.user_id == identity.user_id,
                    col(Wallet.is_primary).is_(True),
                )
            )
        ).scalar_one_or_none()
        if wallet is None:
            raise NftValidationError("Primary wallet is required")
        if not monad_contract_adapter.collectibles_configured:
            raise ChainConfigurationError("Collectible minter configuration is required")

        purchase_key = f"fan-nft-buy:{application.id}:{identity.user_id}"
        await fan_token_service.award(
            session,
            user_id=identity.user_id,
            delta=-application.price_fan_tokens,
            source_type="fan-nft-buy",
            source_id=application.id,
            idempotency_key=f"{purchase_key}:debit",
            description=f"购买限量 NFT：{application.name}",
        )
        claim_hash = monad_contract_adapter.operation_hash(purchase_key)
        mint_operation = ChainOperation(
            user_id=identity.user_id,
            operation_type="FAN_NFT_MINT",
            idempotency_key=purchase_key,
            operation_hash=claim_hash,
            chain_id=settings.monad_chain_id,
            contract_address=token_type.contract_address,
            token_id=token_type.token_id,
            metadata_cid=token_type.metadata_cid,
            request_payload={"wallet": wallet, "amount": 1, "price_fan_tokens": application.price_fan_tokens},
        )
        ownership = CollectibleOwnership(
            token_type_id=token_type.id,
            user_id=identity.user_id,
            wallet_address=wallet,
            amount=0,
            claim_key=claim_hash,
            chain_operation_id=mint_operation.id,
        )
        session.add(mint_operation)
        await session.flush()
        session.add(ownership)
        await session.commit()
        try:
            mint_operation.status = "SUBMITTED"
            await session.commit()
            receipt = await monad_contract_adapter.mint_collectible(wallet, token_type.token_id, 1, claim_hash)
            mint_operation.status = "CONFIRMED"
            mint_operation.transaction_hash = receipt.transaction_hash
            mint_operation.block_number = receipt.block_number
            mint_operation.confirmations = receipt.confirmations
            mint_operation.confirmed_at = utc_now()
            ownership.amount = 1
            ownership.status = "CONFIRMED"
            ownership.minted_at = utc_now()
            token_type.minted_supply += 1
            await fan_token_service.award(
                session,
                user_id=application.user_id,
                delta=application.price_fan_tokens,
                source_type="fan-nft-sale",
                source_id=application.id,
                idempotency_key=f"{purchase_key}:credit",
                description=f"售出限量 NFT：{application.name}",
            )
            await session.commit()
            return ownership
        except Exception:
            mint_operation.status = "RETRYABLE"
            ownership.status = "FAILED"
            await fan_token_service.award(
                session,
                user_id=identity.user_id,
                delta=application.price_fan_tokens,
                source_type="fan-nft-buy-refund",
                source_id=application.id,
                idempotency_key=f"{purchase_key}:refund",
                description=f"购买失败退款：{application.name}",
            )
            await session.commit()
            raise

    async def set_collectible_avatar(
        self,
        session: AsyncSession,
        identity: AuthenticatedIdentity,
        token_type_id: str,
    ) -> str:
        ownership = (
            await session.execute(
                select(CollectibleOwnership).where(
                    CollectibleOwnership.token_type_id == token_type_id,
                    CollectibleOwnership.user_id == identity.user_id,
                    CollectibleOwnership.amount > 0,
                    CollectibleOwnership.status == "CONFIRMED",
                )
            )
        ).scalar_one_or_none()
        if ownership is None:
            raise NftValidationError("A confirmed owned NFT is required")
        token_type = await session.get(CollectibleTokenType, token_type_id)
        profile = await session.get(UserProfile, identity.user_id, with_for_update=True)
        if token_type is None or profile is None:
            raise NftValidationError("NFT or user profile is unavailable")
        metadata = (
            await session.execute(
                select(NftMetadataVersion)
                .where(NftMetadataVersion.metadata_cid == token_type.metadata_cid)
                .order_by(col(NftMetadataVersion.created_at).desc())
                .limit(1)
            )
        ).scalars().first()
        if metadata is None or not metadata.image_cid:
            raise NftValidationError("NFT image is unavailable")
        avatar_url = pinata_adapter.gateway_url(metadata.image_cid)
        profile.avatar_url = avatar_url
        profile.updated_at = utc_now()
        await session.commit()
        return avatar_url

    async def _submit_membership_identity_mint(
        self,
        session: AsyncSession,
        identity: AuthenticatedIdentity,
        record: MembershipIdentityNft,
        operation: ChainOperation,
        *,
        is_retry: bool = False,
    ) -> MembershipIdentityNft:
        try:
            operation.status = "SUBMITTED"
            operation.submitted_at = utc_now()
            operation.failure_reason = None
            if is_retry:
                operation.retry_count += 1
            record.status = "PENDING"
            await session.commit()
            receipt = await monad_contract_adapter.mint_identity(
                identity.primary_wallet,
                record.level_id,
                pinata_adapter.ipfs_uri(record.metadata_cid),
                operation.operation_hash,
            )
            operation.status = "CONFIRMED"
            operation.transaction_hash = receipt.transaction_hash
            operation.block_number = receipt.block_number
            operation.confirmations = receipt.confirmations
            operation.confirmed_at = utc_now()
            record.token_id = int(receipt.event_args["tokenId"])
            operation.token_id = record.token_id
            record.status = "CONFIRMED"
            record.minted_at = utc_now()
            record.updated_at = utc_now()
            await session.commit()
        except Exception as error:
            operation.status = "RETRYABLE"
            operation.failure_reason = str(error)[:500]
            record.status = "RETRYABLE"
            record.updated_at = utc_now()
            await session.commit()
            logger.exception("membership_identity_mint_failed", user_id=identity.user_id)
        return record

    async def ensure_membership_identity(
        self, session: AsyncSession, identity: AuthenticatedIdentity
    ) -> MembershipIdentityNft | None:
        existing = (
            await session.execute(select(MembershipIdentityNft).where(MembershipIdentityNft.user_id == identity.user_id))
        ).scalar_one_or_none()
        profile = await session.get(UserProfile, identity.user_id)
        user = await session.get(User, identity.user_id)
        if profile is None or user is None or not profile.is_official_member:
            return None
        level = await self._identity_level_for_profile(session, profile)
        if level is None:
            raise NftValidationError("Membership level is not configured")

        configured_identity_contract = settings.membership_identity_contract_address.lower()
        identity_contract_changed = (
            existing is not None
            and bool(configured_identity_contract)
            and existing.contract_address.lower() != configured_identity_contract
        )

        if (
            existing is not None
            and existing.token_id is not None
            and existing.level_id == level.rank
            and not identity_contract_changed
        ):
            return existing
        if not pinata_adapter.configured or not settings.membership_identity_contract_address:
            return existing
        if existing is None and not monad_contract_adapter.identity_configured:
            return None
        if identity_contract_changed:
            assert existing is not None
            if not monad_contract_adapter.identity_configured:
                return existing
            version_number = existing.metadata_version + 1
            metadata_version, metadata_cid = await self._pin_membership_metadata(
                identity=identity,
                profile=profile,
                level=level,
                version=version_number,
            )
            idempotency_key = f"identity-mint:{identity.user_id}:{configured_identity_contract}"
            operation_hash = monad_contract_adapter.operation_hash(idempotency_key)
            operation = ChainOperation(
                user_id=identity.user_id,
                operation_type="IDENTITY_MINT",
                idempotency_key=idempotency_key,
                operation_hash=operation_hash,
                chain_id=settings.monad_chain_id,
                contract_address=configured_identity_contract,
                metadata_cid=metadata_cid,
                request_payload={
                    "wallet": identity.primary_wallet,
                    "level_id": level.rank,
                    "previous_contract_address": existing.contract_address,
                    "previous_token_id": existing.token_id,
                },
            )
            session.add(metadata_version)
            session.add(operation)
            existing.wallet_address = identity.primary_wallet
            existing.chain_id = settings.monad_chain_id
            existing.contract_address = configured_identity_contract
            existing.token_id = None
            existing.level_id = level.rank
            existing.level_code = level.code
            existing.metadata_version = version_number
            existing.metadata_cid = metadata_cid
            existing.status = "PENDING"
            existing.chain_operation_id = operation.id
            existing.minted_at = None
            existing.updated_at = utc_now()
            await session.commit()
            return await self._submit_membership_identity_mint(session, identity, existing, operation)
        if existing is not None and existing.token_id is None:
            if existing.status != "RETRYABLE" or not monad_contract_adapter.identity_configured:
                return existing
            operation = (
                await session.get(ChainOperation, existing.chain_operation_id)
                if existing.chain_operation_id
                else None
            )
            if operation is None:
                raise NftValidationError("Membership identity mint operation is missing")
            return await self._submit_membership_identity_mint(
                session,
                identity,
                existing,
                operation,
                is_retry=True,
            )
        if existing is not None and not settings.identity_level_manager_private_key:
            return existing
        version_number = existing.metadata_version + 1 if existing else 1
        metadata_version, metadata_cid = await self._pin_membership_metadata(
            identity=identity,
            profile=profile,
            level=level,
            version=version_number,
        )

        if existing is not None:
            if existing.token_id is None:
                return existing
            idempotency_key = f"identity-level-update:{identity.user_id}:{level.code}:v{version_number}"
            operation_hash = monad_contract_adapter.operation_hash(idempotency_key)
            operation = ChainOperation(
                user_id=identity.user_id,
                operation_type="IDENTITY_LEVEL_UPDATE",
                idempotency_key=idempotency_key,
                operation_hash=operation_hash,
                chain_id=settings.monad_chain_id,
                contract_address=configured_identity_contract,
                token_id=existing.token_id,
                metadata_cid=metadata_cid,
                request_payload={"previous_level_id": existing.level_id, "next_level_id": level.rank},
            )
            session.add(metadata_version)
            session.add(operation)
            existing.status = "PENDING"
            existing.chain_operation_id = operation.id
            await session.commit()
            try:
                operation.status = "SUBMITTED"
                operation.submitted_at = utc_now()
                await session.commit()
                receipt = await monad_contract_adapter.update_membership_level(
                    existing.token_id,
                    level.rank,
                    pinata_adapter.ipfs_uri(metadata_cid),
                    operation_hash,
                )
                operation.status = "CONFIRMED"
                operation.transaction_hash = receipt.transaction_hash
                operation.block_number = receipt.block_number
                operation.confirmations = receipt.confirmations
                operation.confirmed_at = utc_now()
                existing.level_id = level.rank
                existing.level_code = level.code
                existing.metadata_version = version_number
                existing.metadata_cid = metadata_cid
                existing.status = "CONFIRMED"
                existing.updated_at = utc_now()
                await session.commit()
            except Exception as error:
                operation.status = "RETRYABLE"
                operation.failure_reason = str(error)[:500]
                existing.status = "RETRYABLE"
                await session.commit()
                logger.exception("membership_identity_level_update_failed", user_id=identity.user_id)
            return existing

        idempotency_key = f"identity-mint:{identity.user_id}:{configured_identity_contract}"
        operation_hash = monad_contract_adapter.operation_hash(idempotency_key)
        operation = ChainOperation(
            user_id=identity.user_id,
            operation_type="IDENTITY_MINT",
            idempotency_key=idempotency_key,
            operation_hash=operation_hash,
            chain_id=settings.monad_chain_id,
            contract_address=configured_identity_contract,
            metadata_cid=metadata_cid,
            request_payload={"wallet": identity.primary_wallet, "level_id": level.rank},
        )
        record = MembershipIdentityNft(
            user_id=identity.user_id,
            wallet_address=identity.primary_wallet,
            chain_id=settings.monad_chain_id,
            contract_address=configured_identity_contract,
            level_id=level.rank,
            level_code=level.code,
            metadata_cid=metadata_cid,
            chain_operation_id=operation.id,
        )
        session.add(metadata_version)
        session.add(operation)
        session.add(record)
        await session.commit()
        return await self._submit_membership_identity_mint(session, identity, record, operation)

    async def _write_membership_card(
        self,
        session: AsyncSession,
        identity: AuthenticatedIdentity,
        *,
        record: MembershipIdentityNft,
        user: User,
        profile: UserProfile,
        level: MembershipLevel,
    ) -> tuple[MembershipIdentityNft, bool, int]:
        if record.token_id is None or record.status != "CONFIRMED":
            raise NftValidationError("Confirmed membership identity is required")
        level_changed = record.level_id != level.rank
        if not pinata_adapter.configured:
            raise ChainConfigurationError("Pinata configuration is required")
        if level_changed and not settings.identity_level_manager_private_key:
            raise ChainConfigurationError("Identity level manager configuration is required")
        if not level_changed and not monad_contract_adapter.identity_uri_manager_configured:
            raise ChainConfigurationError("Identity URI manager configuration is required")

        content_hash = self.membership_card_content_hash(
            user=user,
            profile=profile,
            level=level,
            record=record,
        )
        if record.is_member_card and record.card_content_hash == content_hash and not level_changed:
            return record, False, 0

        version_number = record.metadata_version + 1
        metadata_version, metadata_cid, content_hash = await self._pin_membership_card_metadata(
            identity=identity,
            user=user,
            profile=profile,
            level=level,
            record=record,
            version=version_number,
        )
        action = "create" if not record.is_member_card else "refresh"
        idempotency_key = f"membership-card-{action}:{identity.user_id}:{record.token_id}:{uuid4().hex}"
        operation = ChainOperation(
            user_id=identity.user_id,
            operation_type="MEMBERSHIP_CARD_LEVEL_UPDATE" if level_changed else "MEMBERSHIP_CARD_METADATA_UPDATE",
            idempotency_key=idempotency_key,
            operation_hash=monad_contract_adapter.operation_hash(idempotency_key),
            chain_id=settings.monad_chain_id,
            contract_address=record.contract_address,
            token_id=record.token_id,
            metadata_cid=metadata_cid,
            request_payload={
                "previous_level_id": record.level_id,
                "next_level_id": level.rank,
                "next_metadata_version": version_number,
                "card_content_hash": content_hash,
                "fee_fan_tokens": 0,
            },
        )
        session.add(metadata_version)
        session.add(operation)
        record.status = "PENDING"
        record.chain_operation_id = operation.id
        operation.status = "SUBMITTED"
        operation.submitted_at = utc_now()
        await session.commit()

        try:
            if level_changed:
                receipt = await monad_contract_adapter.update_membership_level(
                    record.token_id,
                    level.rank,
                    pinata_adapter.ipfs_uri(metadata_cid),
                    operation.operation_hash,
                )
            else:
                receipt = await monad_contract_adapter.update_identity_metadata(
                    record.token_id,
                    pinata_adapter.ipfs_uri(metadata_cid),
                    operation.operation_hash,
                )
            now = utc_now()
            operation.status = "CONFIRMED"
            operation.transaction_hash = receipt.transaction_hash
            operation.block_number = receipt.block_number
            operation.confirmations = receipt.confirmations
            operation.confirmed_at = now
            record.level_id = level.rank
            record.level_code = level.code
            record.metadata_version = version_number
            record.metadata_cid = metadata_cid
            record.is_member_card = True
            record.card_level_code = level.code
            record.card_content_hash = content_hash
            record.card_fee_fan_tokens = 0
            record.card_created_at = record.card_created_at or now
            record.card_updated_at = now
            record.status = "CONFIRMED"
            record.updated_at = now
            await session.commit()
            return record, True, 0
        except Exception as error:
            operation.status = "RETRYABLE"
            operation.failure_reason = str(error)[:500]
            # The existing identity token remains valid when a metadata transaction fails.
            record.status = "CONFIRMED"
            record.updated_at = utc_now()
            await session.delete(metadata_version)
            await session.commit()
            logger.exception(
                "membership_card_update_failed",
                user_id=identity.user_id,
                token_id=record.token_id,
            )
            raise NftValidationError("Membership card transaction failed; no FAN was charged") from error

    async def create_membership_card(
        self,
        session: AsyncSession,
        identity: AuthenticatedIdentity,
    ) -> tuple[MembershipIdentityNft, bool, int]:
        record = await self.ensure_membership_identity(session, identity)
        if record is None or record.token_id is None or record.status != "CONFIRMED":
            raise NftValidationError("Membership identity must be confirmed before creating a card")
        user = await session.get(User, identity.user_id)
        profile = await session.get(UserProfile, identity.user_id, with_for_update=True)
        if user is None or profile is None or not profile.is_official_member:
            raise NftValidationError("Official membership is required")
        level = await self._identity_level_for_profile(session, profile)
        if level is None:
            raise NftValidationError("Membership level is not configured")
        return await self._write_membership_card(
            session,
            identity,
            record=record,
            user=user,
            profile=profile,
            level=level,
        )

    async def refresh_membership_card(
        self,
        session: AsyncSession,
        identity: AuthenticatedIdentity,
    ) -> tuple[MembershipIdentityNft, bool, int]:
        record = (
            await session.execute(
                select(MembershipIdentityNft).where(MembershipIdentityNft.user_id == identity.user_id)
            )
        ).scalar_one_or_none()
        user = await session.get(User, identity.user_id)
        profile = await session.get(UserProfile, identity.user_id, with_for_update=True)
        if record is None or not record.is_member_card or user is None or profile is None:
            raise NftValidationError("A confirmed membership card is required")
        level = await self._identity_level_for_profile(session, profile)
        if level is None:
            raise NftValidationError("Membership level is not configured")
        return await self._write_membership_card(
            session,
            identity,
            record=record,
            user=user,
            profile=profile,
            level=level,
        )

    async def refresh_membership_identity_metadata(
        self,
        session: AsyncSession,
        identity: AuthenticatedIdentity,
    ) -> MembershipIdentityNft:
        record = (
            await session.execute(
                select(MembershipIdentityNft).where(
                    MembershipIdentityNft.user_id == identity.user_id
                )
            )
        ).scalar_one_or_none()
        profile = await session.get(UserProfile, identity.user_id)
        if record is None or record.token_id is None or profile is None:
            raise NftValidationError("Confirmed membership identity is required")
        level = await self._identity_level_for_profile(session, profile)
        if level is None:
            raise NftValidationError("Membership level is not configured")
        if level.rank != record.level_id:
            raise NftValidationError(
                "Membership level must be synchronized before refreshing identity metadata"
            )
        if not pinata_adapter.configured or not monad_contract_adapter.identity_uri_manager_configured:
            raise ChainConfigurationError(
                "Pinata and identity URI manager configuration are required"
            )

        image_cid = await self._pin_membership_level_image(level)
        image_hash = level.badge_image_content_hash or image_cid
        idempotency_key = (
            f"identity-metadata-refresh:{identity.user_id}:{level.code}:{image_hash}"
        )
        operation = (
            await session.execute(
                select(ChainOperation).where(
                    ChainOperation.idempotency_key == idempotency_key
                )
            )
        ).scalar_one_or_none()
        if operation is not None and operation.status == "CONFIRMED":
            return record

        if operation is None:
            version_number = record.metadata_version + 1
            metadata_version, metadata_cid = await self._pin_membership_metadata(
                identity=identity,
                profile=profile,
                level=level,
                version=version_number,
            )
            operation_hash = monad_contract_adapter.operation_hash(idempotency_key)
            operation = ChainOperation(
                user_id=identity.user_id,
                operation_type="IDENTITY_METADATA_UPDATE",
                idempotency_key=idempotency_key,
                operation_hash=operation_hash,
                chain_id=settings.monad_chain_id,
                contract_address=settings.membership_identity_contract_address.lower(),
                token_id=record.token_id,
                metadata_cid=metadata_cid,
                request_payload={
                    "previous_metadata_cid": record.metadata_cid,
                    "next_metadata_version": version_number,
                    "image_content_hash": image_hash,
                },
            )
            session.add(metadata_version)
            session.add(operation)
        else:
            if not operation.metadata_cid:
                raise NftValidationError("Retryable metadata operation is missing its CID")
            metadata_cid = operation.metadata_cid
            version_number = int(operation.request_payload["next_metadata_version"])
            operation.retry_count += 1

        record.status = "PENDING"
        record.chain_operation_id = operation.id
        operation.status = "SUBMITTED"
        operation.submitted_at = utc_now()
        operation.failure_reason = None
        await session.commit()
        try:
            receipt = await monad_contract_adapter.update_identity_metadata(
                record.token_id,
                pinata_adapter.ipfs_uri(metadata_cid),
                operation.operation_hash,
            )
            operation.status = "CONFIRMED"
            operation.transaction_hash = receipt.transaction_hash
            operation.block_number = receipt.block_number
            operation.confirmations = receipt.confirmations
            operation.confirmed_at = utc_now()
            record.metadata_version = version_number
            record.metadata_cid = metadata_cid
            record.status = "CONFIRMED"
            record.updated_at = utc_now()
            await session.commit()
        except Exception as error:
            operation.status = "RETRYABLE"
            operation.failure_reason = str(error)[:500]
            record.status = "RETRYABLE"
            record.updated_at = utc_now()
            await session.commit()
            logger.exception(
                "membership_identity_metadata_update_failed",
                user_id=identity.user_id,
                token_id=record.token_id,
            )
        return record

    async def process_custom_badge(self, session: AsyncSession, application: NftApplication) -> NftApplication:
        if application.status not in {"APPROVED", "FAILED"}:
            raise NftValidationError("Only approved or retryable applications can be processed")
        if not pinata_adapter.configured or not monad_contract_adapter.collectibles_configured:
            raise ChainConfigurationError("Pinata and collectible operator configuration are required")
        if not application.image_data:
            raise NftValidationError("Application image is unavailable")
        content, mime_type, _, _ = self._parse_image(application.image_data)
        application.status = "PINNING"
        await session.commit()
        try:
            image = await pinata_adapter.pin_image(f"custom-badge-{application.id}", content, mime_type)
            metadata_payload = {
                "name": application.name,
                "description": application.description,
                "image": pinata_adapter.ipfs_uri(image.cid),
                "category": "CUSTOM_BADGE",
                "issuer": settings.fanora_issuer_name,
                "theme": application.theme,
                "attributes": application.public_attributes
                + [{"trait_type": "Category", "value": "CUSTOM_BADGE"}, {"trait_type": "Max Supply", "value": "1"}],
            }
            metadata = await pinata_adapter.pin_metadata(f"custom-badge-{application.id}-v1.json", metadata_payload)
            version = NftMetadataVersion(
                subject_type="CUSTOM_BADGE",
                subject_id=application.id,
                version=1,
                image_cid=image.cid,
                image_pin_id=image.pin_id,
                metadata_cid=metadata.cid,
                metadata_pin_id=metadata.pin_id,
                content_hash=hashlib.sha256(content).hexdigest(),
                size_bytes=len(content),
                mime_type=mime_type,
                metadata_payload=metadata_payload,
                created_by_user_id=application.user_id,
            )
            max_token_id = (
                await session.execute(select(func.max(CollectibleTokenType.token_id)))
            ).scalar_one_or_none() or 0
            token_id = int(max_token_id) + 1
            now = datetime.now(UTC)
            token_type = CollectibleTokenType(
                token_id=token_id,
                category="CUSTOM_BADGE",
                name=application.name,
                description=application.description,
                chain_id=settings.monad_chain_id,
                contract_address=settings.collectibles_contract_address.lower(),
                metadata_cid=metadata.cid,
                max_supply=1,
                per_wallet_limit=1,
                mint_start=now - timedelta(minutes=1),
                mint_end=now + timedelta(days=3650),
                transferable=False,
                source_type="NFT_APPLICATION",
                source_id=application.id,
            )
            create_key = f"collectible-type-create:{application.id}:v1"
            create_operation = ChainOperation(
                user_id=application.user_id,
                operation_type="COLLECTIBLE_TYPE_CREATE",
                idempotency_key=create_key,
                operation_hash=monad_contract_adapter.operation_hash(create_key),
                chain_id=settings.monad_chain_id,
                contract_address=settings.collectibles_contract_address.lower(),
                token_id=token_id,
                metadata_cid=metadata.cid,
                request_payload={"category": "CUSTOM_BADGE", "max_supply": 1},
            )
            session.add(version)
            session.add(token_type)
            session.add(create_operation)
            await session.flush()
            application.metadata_version_id = version.id
            application.collectible_token_type_id = token_type.id
            application.status = "MINTING"
            await session.commit()
            create_operation.status = "SUBMITTED"
            await session.commit()
            receipt = await monad_contract_adapter.create_token_type(
                {
                    "token_id": token_id,
                    "category": 1,
                    "metadata_uri": pinata_adapter.ipfs_uri(metadata.cid),
                    "max_supply": 1,
                    "per_wallet_limit": 1,
                    "mint_start": int(token_type.mint_start.timestamp()),
                    "mint_end": int(token_type.mint_end.timestamp()),
                    "transferable": False,
                }
            )
            create_operation.status = "CONFIRMED"
            create_operation.transaction_hash = receipt.transaction_hash
            create_operation.block_number = receipt.block_number
            create_operation.confirmations = receipt.confirmations
            create_operation.confirmed_at = utc_now()
            token_type.status = "CONFIRMED"
            await session.commit()

            wallet = (
                await session.execute(
                    select(MembershipIdentityNft.wallet_address).where(MembershipIdentityNft.user_id == application.user_id)
                )
            ).scalar_one_or_none()
            if wallet is None:
                from app.models.user import Wallet
                wallet = (
                    await session.execute(select(Wallet.address).where(Wallet.user_id == application.user_id, col(Wallet.is_primary).is_(True)))
                ).scalar_one()
            claim_key = f"custom-badge-mint:{application.id}:v1"
            claim_hash = monad_contract_adapter.operation_hash(claim_key)
            mint_operation = ChainOperation(
                user_id=application.user_id,
                operation_type="COLLECTIBLE_MINT",
                idempotency_key=claim_key,
                operation_hash=claim_hash,
                chain_id=settings.monad_chain_id,
                contract_address=settings.collectibles_contract_address.lower(),
                token_id=token_id,
                metadata_cid=metadata.cid,
                request_payload={"wallet": wallet, "amount": 1},
            )
            ownership = CollectibleOwnership(
                token_type_id=token_type.id,
                user_id=application.user_id,
                wallet_address=wallet,
                amount=0,
                claim_key=claim_hash,
                chain_operation_id=mint_operation.id,
            )
            session.add(mint_operation)
            await session.flush()
            session.add(ownership)
            await session.commit()
            mint_operation.status = "SUBMITTED"
            await session.commit()
            mint_receipt = await monad_contract_adapter.mint_collectible(wallet, token_id, 1, claim_hash)
            mint_operation.status = "CONFIRMED"
            mint_operation.transaction_hash = mint_receipt.transaction_hash
            mint_operation.block_number = mint_receipt.block_number
            mint_operation.confirmations = mint_receipt.confirmations
            mint_operation.confirmed_at = utc_now()
            ownership.amount = 1
            ownership.status = "CONFIRMED"
            ownership.minted_at = utc_now()
            token_type.minted_supply = 1
            application.status = "MINTED"
            application.image_data = None
            await session.commit()
            return application
        except Exception:
            application_id = application.id
            await session.rollback()
            failed_application = await session.get(NftApplication, application_id)
            if failed_application is not None:
                failed_application.status = "FAILED"
                failed_application.updated_at = utc_now()
                await session.commit()
            raise


nft_service = NftService()
