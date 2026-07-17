"""Structured input and output for the Fanora profile Agent."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

FanType = Literal["emerging_fan", "loyal_fan", "advocate", "core_contributor"]


class FanProfileRequest(BaseModel):
    wallet_address: str
    community_id: str = Field(min_length=1, max_length=100)
    points: int = Field(default=0, ge=0)
    completed_tasks: int = Field(default=0, ge=0)
    active_days: int = Field(default=0, ge=0)
    referrals: int = Field(default=0, ge=0)
    onchain_actions: int = Field(default=0, ge=0)

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet_address(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized.startswith("0x") or len(normalized) != 42:
            raise ValueError("wallet_address must be a 20-byte EVM address")
        try:
            int(normalized[2:], 16)
        except ValueError as error:
            raise ValueError("wallet_address must be hexadecimal") from error
        return normalized


class FanProfileScores(BaseModel):
    activity: int = Field(ge=0, le=100)
    loyalty: int = Field(ge=0, le=100)
    influence: int = Field(ge=0, le=100)
    contribution: int = Field(ge=0, le=100)
    total: int = Field(ge=0, le=100)


class BadgeDraft(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1, max_length=500)
    level: str = Field(min_length=1, max_length=50)


class FanProfileNarrative(BaseModel):
    fan_type: FanType
    summary: str = Field(min_length=1, max_length=600)
    badge_name: str | None = Field(default=None, max_length=100)
    badge_description: str | None = Field(default=None, max_length=500)


class FanProfileAnalysis(BaseModel):
    run_id: str
    wallet_address: str
    community_id: str
    scores: FanProfileScores
    fan_type: FanType
    summary: str
    analysis_source: Literal["rules", "llm"]
    badge_eligible: bool
    badge_draft: BadgeDraft | None = None
