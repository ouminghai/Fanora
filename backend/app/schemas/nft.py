"""NFT, collection, chain synchronization, and custom badge schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PublicAttribute(BaseModel):
    trait_type: str = Field(min_length=1, max_length=60)
    value: str = Field(min_length=1, max_length=120)


class NftApplicationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=10, max_length=1000)
    theme: str = Field(min_length=2, max_length=120)
    public_attributes: list[PublicAttribute] = Field(default_factory=list, max_length=12)
    copyright_declaration: str = Field(min_length=10, max_length=500)
    image_data_url: str = Field(min_length=32, max_length=7_000_000)

    @field_validator("image_data_url")
    @classmethod
    def validate_image_data_url(cls, value: str) -> str:
        if not value.startswith("data:image/") or ";base64," not in value[:100]:
            raise ValueError("image_data_url must be a base64 image data URL")
        return value


class NftApplicationReview(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    reason: str | None = Field(default=None, max_length=500)
    internal_note: str | None = Field(default=None, max_length=1000)


class NftApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    theme: str
    public_attributes: list[dict[str, str]]
    copyright_declaration: str
    image_data_url: str | None = None
    status: str
    rejection_reason: str | None
    metadata_version_id: str | None
    collectible_token_type_id: str | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ChainOperationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    operation_type: str
    status: str
    transaction_hash: str | None
    block_number: int | None
    confirmations: int
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


class MembershipIdentityResponse(BaseModel):
    token_id: int | None
    level_id: int
    level_code: str
    metadata_version: int
    metadata_uri: str
    image_url: str | None
    status: str
    contract_address: str
    chain_id: int
    explorer_url: str | None
    operation: ChainOperationResponse | None


class CollectibleResponse(BaseModel):
    token_type_id: str
    token_id: int
    category: str
    name: str
    description: str
    metadata_uri: str
    image_url: str | None
    amount: int
    max_supply: int
    minted_supply: int
    transferable: bool
    status: str
    contract_address: str
    chain_id: int
    explorer_url: str | None
    operation: ChainOperationResponse | None


class MyCollectionResponse(BaseModel):
    chain_id: int
    network_name: str = "Monad Testnet"
    identity_sync_status: str
    identity: MembershipIdentityResponse | None
    collectibles: list[CollectibleResponse]
    applications: list[NftApplicationResponse]
