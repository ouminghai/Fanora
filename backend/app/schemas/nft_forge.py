"""Schemas for the auditable, off-chain NFT Memory Forge game."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.auth import validate_image_url
from app.schemas.nft import PublicAttribute

ForgeMode = Literal["STABLE", "FOCUSED", "LEGENDARY"]


class NftForgeAnalyzeRequest(BaseModel):
    conversation_id: str | None = Field(default=None, max_length=80)
    template_id: str | None = Field(default=None, max_length=64)
    visual_style: str = Field(default="cinematic", min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=100)
    story_summary: str = Field(min_length=10, max_length=1500)
    description: str = Field(min_length=10, max_length=1000)
    image_prompt: str = Field(min_length=10, max_length=2500)
    image_url: str = Field(min_length=12, max_length=7_000_000)
    reference_image_urls: list[str] = Field(default_factory=list, max_length=6)
    suggested_attributes: list[PublicAttribute] = Field(default_factory=list, max_length=8)
    supply: int = Field(default=50, ge=1, le=1000)
    price_fan_tokens: int = Field(default=20, ge=1, le=1_000_000)
    forge_mode: ForgeMode = "FOCUSED"
    copyright_confirmed: bool = False

    @field_validator("reference_image_urls")
    @classmethod
    def validate_references(cls, value: list[str]) -> list[str]:
        return [validate_image_url(item, label="Forge reference") or "" for item in value]

    @field_validator("image_url")
    @classmethod
    def validate_generated_image(cls, value: str) -> str:
        return validate_image_url(value, label="Generated NFT image", max_bytes=7_000_000) or ""


class NftForgeStrategyRequest(BaseModel):
    supply: int = Field(ge=1, le=1000000)
    price_fan_tokens: int = Field(ge=1, le=1_000_000_000)
    forge_mode: ForgeMode


class NftForgeStartRequest(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=160, pattern=r"^[a-zA-Z0-9:_-]+$")
    use_fragment_credit: bool = False


class NftForgeSelectVersionRequest(BaseModel):
    version_id: str = Field(min_length=4, max_length=64)


class NftFragmentRedeemRequest(BaseModel):
    forge_mode: Literal["STABLE", "FOCUSED"]
    idempotency_key: str = Field(min_length=8, max_length=160, pattern=r"^[a-zA-Z0-9:_-]+$")


class NftForgeAnalysisResponse(BaseModel):
    rare_score: int
    rarity_level: str
    dimensions: dict[str, int]
    recommend_supply: dict[str, int]
    recommend_price: dict[str, int]
    suggestions: list[str]
    model_name: str
    prompt_version: str


class NftForgeProbabilityResponse(BaseModel):
    quality_factor: float
    strategy_fit: float
    price_fit: float
    level_bonus: float
    mode_modifier: float
    success_rate: float
    perfect_rate: float
    fan_cost: int
    possible_results: list[str]


class NftForgeAttemptResponse(BaseModel):
    id: str
    forge_mode: str
    payment_source: str
    fan_cost: int
    success_rate: float
    perfect_rate: float
    random_roll: float
    perfect_roll: float | None
    server_seed_hash: str
    server_seed_reveal: str | None
    result: str
    refund_status: str
    error_message: str | None
    rules_version: str
    created_at: datetime
    completed_at: datetime | None


class NftForgeSessionResponse(BaseModel):
    id: str
    conversation_id: str | None
    status: str
    title: str
    story_summary: str
    image_prompt: str
    reference_image_urls: list[str]
    suggested_attributes: list[dict[str, str]]
    supply: int
    price_fan_tokens: int
    forge_mode: str
    rules_version: str
    generated_versions: list[dict[str, object]]
    selected_version_id: str | None
    analysis: NftForgeAnalysisResponse
    probability: NftForgeProbabilityResponse
    latest_attempt: NftForgeAttemptResponse | None
    fragment_balance: int
    stable_credits: int
    focused_credits: int
    fan_token_balance: int
    created_at: datetime
    updated_at: datetime


class NftFragmentLedgerResponse(BaseModel):
    id: str
    delta: int
    balance_after: int
    source_type: str
    description: str
    created_at: datetime


class NftFragmentBalanceResponse(BaseModel):
    balance: int
    stable_credits: int
    focused_credits: int
    stable_redeem_cost: int
    focused_redeem_cost: int
    ledger: list[NftFragmentLedgerResponse]
