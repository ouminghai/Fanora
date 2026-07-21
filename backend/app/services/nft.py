"""NFT orchestration across deterministic rules, Pinata, PostgreSQL, and Monad."""

import base64
import hashlib
import io
import json
import mimetypes
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from PIL import Image, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from app.adapters.monad import ChainConfigurationError, monad_contract_adapter
from app.adapters.pinata import PinataConfigurationError, pinata_adapter
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
from app.models.user import User, UserProfile
from app.schemas.nft import NftApplicationCreate
from app.services.identity import AuthenticatedIdentity

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


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
            raise NftValidationError("Only JPEG, PNG, and WebP images are supported")
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

    async def _pin_membership_level_image(self, level: MembershipLevel) -> str:
        if level.badge_image_cid:
            return level.badge_image_cid
        source = level.badge_image_url.strip()
        if source.startswith("ipfs://"):
            level.badge_image_cid = source.removeprefix("ipfs://")
            return level.badge_image_cid
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
        content_hash = hashlib.sha256(content).hexdigest()
        pinned = await pinata_adapter.pin_image(f"membership-level-{level.code}", content, mime_type)
        level.badge_image_cid = pinned.cid
        level.badge_image_pin_id = pinned.pin_id
        level.badge_image_content_hash = content_hash
        return pinned.cid

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
            "name": f"Fanora Membership · {profile.level}",
            "description": level.description,
            "image": pinata_adapter.ipfs_uri(image_cid),
            "external_url": "https://fanora.xyz",
            "issuer": settings.fanora_issuer_name,
            "proof_of_fandom": {
                "summary": f"Verified Fanora member at {profile.level} level.",
                "version": version,
            },
            "attributes": [
                {"trait_type": "Membership Level", "value": profile.level},
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

    async def create_application(
        self, session: AsyncSession, identity: AuthenticatedIdentity, payload: NftApplicationCreate
    ) -> NftApplication:
        content, mime_type, width, height = self._parse_image(payload.image_data_url)
        application = NftApplication(
            user_id=identity.user_id,
            name=payload.name.strip(),
            description=payload.description.strip(),
            theme=payload.theme.strip(),
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
        level = (
            await session.execute(select(MembershipLevel).where(MembershipLevel.name == profile.level))
        ).scalar_one_or_none()
        if level is None:
            raise NftValidationError("Membership level is not configured")

        if existing is not None and existing.level_id == level.rank:
            return existing
        if not pinata_adapter.configured or not settings.membership_identity_contract_address:
            return existing
        if existing is None and not monad_contract_adapter.identity_configured:
            return None
        if existing is not None and not settings.identity_level_manager_private_key:
            return existing
        if existing is not None and level.rank < existing.level_id:
            raise NftValidationError("Automatic membership identity downgrade is not allowed")

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
                contract_address=settings.membership_identity_contract_address.lower(),
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

        idempotency_key = f"identity-mint:{identity.user_id}"
        operation_hash = monad_contract_adapter.operation_hash(idempotency_key)
        operation = ChainOperation(
            user_id=identity.user_id,
            operation_type="IDENTITY_MINT",
            idempotency_key=idempotency_key,
            operation_hash=operation_hash,
            chain_id=settings.monad_chain_id,
            contract_address=settings.membership_identity_contract_address.lower(),
            metadata_cid=metadata_cid,
            request_payload={"wallet": identity.primary_wallet, "level_id": level.rank},
        )
        record = MembershipIdentityNft(
            user_id=identity.user_id,
            wallet_address=identity.primary_wallet,
            chain_id=settings.monad_chain_id,
            contract_address=settings.membership_identity_contract_address.lower(),
            level_id=level.rank,
            level_code=level.code,
            metadata_cid=metadata_cid,
            chain_operation_id=operation.id,
        )
        session.add(metadata_version)
        session.add(operation)
        session.add(record)
        await session.commit()
        try:
            operation.status = "SUBMITTED"
            operation.submitted_at = utc_now()
            await session.commit()
            receipt = await monad_contract_adapter.mint_identity(
                identity.primary_wallet, level.rank, pinata_adapter.ipfs_uri(metadata_cid), operation_hash
            )
            operation.status = "CONFIRMED"
            operation.transaction_hash = receipt.transaction_hash
            operation.block_number = receipt.block_number
            operation.confirmations = receipt.confirmations
            operation.confirmed_at = utc_now()
            record.token_id = int(receipt.event_args["tokenId"])
            record.status = "CONFIRMED"
            record.minted_at = utc_now()
            await session.commit()
        except Exception as error:
            operation.status = "RETRYABLE"
            operation.failure_reason = str(error)[:500]
            record.status = "RETRYABLE"
            await session.commit()
            logger.exception("membership_identity_mint_failed", user_id=identity.user_id)
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
        except (Exception, PinataConfigurationError):
            application.status = "FAILED"
            application.updated_at = utc_now()
            await session.commit()
            raise


nft_service = NftService()
