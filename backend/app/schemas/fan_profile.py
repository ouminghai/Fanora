"""Structured input and output for the Fanora profile Agent."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

FanType = Literal["emerging_fan", "loyal_fan", "advocate", "active_fan", "early_supporter", "high_value_contributor"]
RiskLevel = Literal["low", "medium", "high"]


class FanProfileRequest(BaseModel):
    wallet_address: str
    fan_token_balance: int = Field(default=0, ge=0)
    completed_tasks: int = Field(default=0, ge=0)
    active_days: int = Field(default=0, ge=0)
    referrals: int = Field(default=0, ge=0)
    onchain_actions: int = Field(default=0, ge=0)
    chain_summary: dict[str, Any] = Field(default_factory=dict)
    risk_signals: list[str] = Field(default_factory=list, max_length=20)

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
    image_prompt: str = Field(min_length=1, max_length=500)
    suggested_attributes: list[dict[str, str]] = Field(default_factory=list, max_length=12)


class FanProfileNarrative(BaseModel):
    fan_type: FanType
    summary: str = Field(min_length=1, max_length=600)
    badge_name: str | None = Field(default=None, max_length=100)
    badge_description: str | None = Field(default=None, max_length=500)
    image_prompt: str | None = Field(default=None, max_length=500)


class TaskRecommendation(BaseModel):
    task_id: str
    title: str
    reason: str = Field(min_length=1, max_length=300)
    reward_fan_tokens: int = Field(ge=0)
    action_url: str


class FanProfileAnalysis(BaseModel):
    run_id: str
    wallet_address: str
    scores: FanProfileScores
    fan_type: FanType
    labels: list[str]
    risk_level: RiskLevel
    summary: str
    analysis_source: Literal["rules", "llm"]
    degraded: bool
    rule_version: str
    prompt_version: str
    model_id: str
    badge_eligible: bool
    badge_draft: BadgeDraft | None = None
    recommended_tasks: list[TaskRecommendation] = Field(default_factory=list, max_length=8)


class PublicFanProfileAnalysis(BaseModel):
    scores: FanProfileScores
    fan_type: FanType
    labels: list[str]
    summary: str
    analysis_source: Literal["rules", "llm"]
    degraded: bool
