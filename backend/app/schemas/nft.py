"""NFT, collection, chain synchronization, and custom badge schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PublicAttribute(BaseModel):
    trait_type: str = Field(min_length=1, max_length=60)
    value: str = Field(min_length=1, max_length=120)


class NftApplicationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str = Field(min_length=2, max_length=1000)
    theme: str = Field(min_length=2, max_length=120)
    price_fan_tokens: int = Field(ge=1, le=1_000_000)
    max_supply: int = Field(ge=1, le=1_000)
    public_attributes: list[PublicAttribute] = Field(default_factory=list, max_length=12)
    copyright_declaration: str = Field(min_length=10, max_length=500)
    image_data_url: str = Field(min_length=32, max_length=7_000_000)
    story_image_urls: list[str] = Field(default_factory=list, max_length=6)

    @field_validator("image_data_url")
    @classmethod
    def validate_image_data_url(cls, value: str) -> str:
        if not value.startswith("data:image/") or ";base64," not in value[:100]:
            raise ValueError("image_data_url must be a base64 image data URL")
        return value

    @field_validator("story_image_urls")
    @classmethod
    def validate_story_image_urls(cls, value: list[str]) -> list[str]:
        for image_url in value:
            if image_url.startswith(("http://", "https://")):
                continue
            if not image_url.startswith("data:image/") or ";base64," not in image_url[:100]:
                raise ValueError("story images must be remote image URLs or base64 image data URLs")
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
    story_image_urls: list[str] = Field(default_factory=list)
    theme: str
    public_attributes: list[dict[str, str]]
    copyright_declaration: str
    price_fan_tokens: int
    max_supply: int
    publish_fee_fan_tokens: int
    image_data_url: str | None = None
    status: str
    rejection_reason: str | None
    metadata_version_id: str | None
    collectible_token_type_id: str | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class NftCreatorResponse(BaseModel):
    id: str
    display_name: str
    avatar_url: str | None
    level: str


class FanNftMintRecordResponse(BaseModel):
    id: str
    wallet_address: str
    amount: int
    status: str
    transaction_hash: str | None
    block_number: int | None
    minted_at: datetime | None
    created_at: datetime
    buyer: NftCreatorResponse


class FanNftListingResponse(BaseModel):
    id: str
    token_type_id: str | None
    token_id: int | None
    name: str
    description: str
    story_image_urls: list[str] = Field(default_factory=list)
    theme: str
    public_attributes: list[dict[str, str]]
    price_fan_tokens: int
    max_supply: int
    minted_supply: int
    remaining_supply: int
    image_url: str | None
    metadata_uri: str | None
    status: str
    contract_address: str | None
    chain_id: int
    explorer_url: str | None
    like_count: int
    favorite_count: int
    liked: bool
    favorited: bool
    mint_records: list[FanNftMintRecordResponse] = Field(default_factory=list)
    creator: NftCreatorResponse
    created_at: datetime
    updated_at: datetime


class FanNftEngagementResponse(BaseModel):
    creation_id: str
    liked: bool
    favorited: bool
    like_count: int
    favorite_count: int


class FanNftCreateResponse(BaseModel):
    listing: FanNftListingResponse
    fan_token_balance: int


class FanNftPurchaseResponse(BaseModel):
    listing: FanNftListingResponse
    collectible: "CollectibleResponse"
    fan_token_balance: int


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
    metadata_gateway_url: str
    image_url: str | None
    download_url: str | None
    is_member_card: bool
    card_needs_refresh: bool
    card_fee_fan_tokens: int
    card_created_at: datetime | None
    card_updated_at: datetime | None
    status: str
    contract_address: str
    chain_id: int
    explorer_url: str | None
    minted_at: datetime | None
    mint_operation: ChainOperationResponse | None
    operation: ChainOperationResponse | None


class CollectibleResponse(BaseModel):
    token_type_id: str
    fan_nft_creation_id: str | None = None
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


class CollectibleAvatarResponse(BaseModel):
    token_type_id: str
    avatar_url: str


class MyCollectionResponse(BaseModel):
    chain_id: int
    network_name: str = "Monad Testnet"
    identity_sync_status: str
    identity: MembershipIdentityResponse | None
    collectibles: list[CollectibleResponse]
    applications: list[NftApplicationResponse]


class PublicCollectionUserResponse(BaseModel):
    id: str
    display_name: str
    username: str | None
    avatar_url: str | None
    bio: str | None
    level: str
    is_official_member: bool
    official_member_since: datetime | None
    fan_token_balance: int
    fan_token_lifetime_earned: int
    fan_type: str
    created_at: datetime


class PublicCollectionResponse(BaseModel):
    chain_id: int
    network_name: str = "Monad Testnet"
    user: PublicCollectionUserResponse
    identity: MembershipIdentityResponse | None
    collectibles: list[CollectibleResponse]
    creations: list[FanNftListingResponse]


class MembershipCardActionResponse(BaseModel):
    collection: MyCollectionResponse
    fan_token_balance: int
    fee_charged: int
    changed: bool
