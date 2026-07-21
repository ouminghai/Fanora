"""NFT metadata, chain operations, issued assets, and custom badge applications."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, CheckConstraint, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import new_id, utc_now


class NftMetadataVersion(SQLModel, table=True):
    __tablename__ = "nft_metadata_versions"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("subject_type", "subject_id", "version", name="uq_nft_metadata_version"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    subject_type: str = Field(max_length=30, index=True)
    subject_id: str = Field(max_length=64, index=True)
    version: int = Field(ge=1)
    image_cid: str = Field(max_length=255)
    image_pin_id: str | None = Field(default=None, max_length=255)
    metadata_cid: str = Field(max_length=255, index=True)
    metadata_pin_id: str | None = Field(default=None, max_length=255)
    content_hash: str = Field(max_length=64)
    size_bytes: int = Field(ge=0)
    mime_type: str = Field(max_length=100)
    pin_status: str = Field(default="PINNED", max_length=20, index=True)
    metadata_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_by_user_id: str | None = Field(default=None, foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)


class ChainOperation(SQLModel, table=True):
    __tablename__ = "chain_operations"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_chain_operation_idempotency_key"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str | None = Field(default=None, foreign_key="users.id", index=True)
    operation_type: str = Field(max_length=40, index=True)
    idempotency_key: str = Field(max_length=160, index=True)
    operation_hash: str = Field(max_length=66, unique=True, index=True)
    chain_id: int = Field(index=True)
    contract_address: str = Field(max_length=42, index=True)
    token_id: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    metadata_cid: str | None = Field(default=None, max_length=255)
    status: str = Field(default="PENDING", max_length=30, index=True)
    transaction_hash: str | None = Field(default=None, max_length=66, index=True)
    block_number: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    confirmations: int = Field(default=0, ge=0)
    request_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    failure_reason: str | None = Field(default=None, max_length=500)
    retry_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utc_now)
    submitted_at: datetime | None = Field(default=None)
    confirmed_at: datetime | None = Field(default=None)
    updated_at: datetime = Field(default_factory=utc_now)


class MembershipIdentityNft(SQLModel, table=True):
    __tablename__ = "membership_identity_nfts"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_membership_identity_user"),
        UniqueConstraint("chain_id", "contract_address", "token_id", name="uq_membership_identity_token"),
    )

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    wallet_address: str = Field(max_length=42, index=True)
    chain_id: int = Field(index=True)
    contract_address: str = Field(max_length=42, index=True)
    token_id: int | None = Field(default=None, sa_column=Column(BigInteger, nullable=True))
    level_id: int = Field(sa_column=Column(BigInteger, nullable=False))
    level_code: str = Field(max_length=50)
    metadata_version: int = Field(default=1, ge=1)
    metadata_cid: str = Field(max_length=255)
    status: str = Field(default="PENDING", max_length=30, index=True)
    chain_operation_id: str | None = Field(default=None, foreign_key="chain_operations.id")
    minted_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CollectibleTokenType(SQLModel, table=True):
    __tablename__ = "collectible_token_types"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("chain_id", "contract_address", "token_id", name="uq_collectible_token_type"),
        CheckConstraint("max_supply > 0", name="ck_collectible_max_supply_positive"),
        CheckConstraint("per_wallet_limit > 0", name="ck_collectible_wallet_limit_positive"),
    )

    id: str = Field(default_factory=new_id, primary_key=True)
    token_id: int = Field(sa_column=Column(BigInteger, nullable=False, index=True))
    category: str = Field(max_length=30, index=True)
    name: str = Field(max_length=100)
    description: str = Field(max_length=1000)
    chain_id: int = Field(index=True)
    contract_address: str = Field(max_length=42, index=True)
    metadata_cid: str = Field(max_length=255)
    max_supply: int = Field(sa_column=Column(BigInteger, nullable=False))
    minted_supply: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    per_wallet_limit: int = Field(sa_column=Column(BigInteger, nullable=False))
    mint_start: datetime
    mint_end: datetime
    transferable: bool = Field(default=False)
    metadata_frozen: bool = Field(default=False)
    active: bool = Field(default=True, index=True)
    source_type: str = Field(max_length=30)
    source_id: str = Field(max_length=64, index=True)
    status: str = Field(default="PENDING", max_length=30, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CollectibleOwnership(SQLModel, table=True):
    __tablename__ = "collectible_ownerships"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("token_type_id", "user_id", name="uq_collectible_ownership"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    token_type_id: str = Field(foreign_key="collectible_token_types.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    wallet_address: str = Field(max_length=42, index=True)
    amount: int = Field(default=0, sa_column=Column(BigInteger, nullable=False))
    claim_key: str = Field(max_length=66, unique=True, index=True)
    status: str = Field(default="PENDING", max_length=30, index=True)
    chain_operation_id: str | None = Field(default=None, foreign_key="chain_operations.id")
    minted_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class NftApplication(SQLModel, table=True):
    __tablename__ = "nft_applications"  # pyright: ignore[reportAssignmentType]

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    name: str = Field(max_length=100)
    description: str = Field(max_length=1000)
    theme: str = Field(max_length=120)
    public_attributes: list[dict[str, str]] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    copyright_declaration: str = Field(max_length=500)
    image_data: str | None = Field(default=None, max_length=7_000_000)
    image_mime_type: str = Field(max_length=100)
    image_size_bytes: int = Field(ge=0)
    image_width: int = Field(ge=0)
    image_height: int = Field(ge=0)
    status: str = Field(default="DRAFT", max_length=30, index=True)
    rejection_reason: str | None = Field(default=None, max_length=500)
    internal_review_note: str | None = Field(default=None, max_length=1000)
    metadata_version_id: str | None = Field(default=None, foreign_key="nft_metadata_versions.id")
    collectible_token_type_id: str | None = Field(default=None, foreign_key="collectible_token_types.id")
    reviewed_by_user_id: str | None = Field(default=None, foreign_key="users.id")
    submitted_at: datetime | None = Field(default=None)
    reviewed_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
