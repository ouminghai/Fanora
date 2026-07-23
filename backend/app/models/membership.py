"""Database-configured membership levels and point award rules."""

from datetime import datetime

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import utc_now


class MembershipLevel(SQLModel, table=True):
    __tablename__ = "membership_levels"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("name", name="uq_membership_level_name"),
        UniqueConstraint("rank", name="uq_membership_level_rank"),
        CheckConstraint("rank > 0", name="ck_membership_level_rank_positive"),
        CheckConstraint(
            "(is_management AND min_token_balance IS NULL AND max_token_balance IS NULL) OR "
            "(NOT is_management AND min_token_balance IS NOT NULL)",
            name="ck_membership_level_token_range",
        ),
        CheckConstraint(
            "max_token_balance IS NULL OR min_token_balance IS NULL OR max_token_balance >= min_token_balance",
            name="ck_membership_level_max_token_balance",
        ),
    )

    code: str = Field(primary_key=True, max_length=50)
    name: str = Field(max_length=30, index=True)
    description: str = Field(max_length=200)
    rank: int = Field(index=True)
    min_token_balance: int | None = Field(default=None, index=True)
    max_token_balance: int | None = Field(default=None)
    badge_image_url: str = Field(max_length=2048)
    badge_image_cid: str | None = Field(default=None, max_length=255)
    badge_image_pin_id: str | None = Field(default=None, max_length=255)
    badge_image_content_hash: str | None = Field(default=None, max_length=64)
    is_management: bool = Field(default=False, index=True)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class FanTokenRule(SQLModel, table=True):
    __tablename__ = "fan_token_rules"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        CheckConstraint("token_delta <> 0", name="ck_fan_token_rule_nonzero_delta"),
        CheckConstraint("daily_limit IS NULL OR daily_limit > 0", name="ck_fan_token_rule_daily_limit"),
        CheckConstraint("monthly_limit IS NULL OR monthly_limit > 0", name="ck_fan_token_rule_monthly_limit"),
        UniqueConstraint("sort_order", name="uq_fan_token_rule_sort_order"),
    )

    code: str = Field(primary_key=True, max_length=60)
    name: str = Field(max_length=80, index=True)
    description: str = Field(max_length=300)
    category: str = Field(max_length=30, index=True)
    token_delta: int
    verification_method: str = Field(max_length=30)
    repeat_policy: str = Field(max_length=30)
    daily_limit: int | None = Field(default=None)
    monthly_limit: int | None = Field(default=None)
    requires_review: bool = Field(default=False, index=True)
    is_active: bool = Field(default=True, index=True)
    sort_order: int = Field(index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class FanTokenConfig(SQLModel, table=True):
    __tablename__ = "fan_token_config"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (CheckConstraint("decimals >= 0 AND decimals <= 18", name="ck_fan_token_config_decimals"),)

    id: str = Field(default="default", primary_key=True, max_length=30)
    name: str = Field(default="Fan Token", max_length=50)
    symbol: str = Field(default="FAN", max_length=12)
    icon_key: str = Field(default="ethereum-diamond", max_length=50)
    decimals: int = Field(default=0)
    is_onchain: bool = Field(default=False)
    chain_id: int | None = Field(default=None)
    contract_address: str | None = Field(default=None, max_length=42)
    description: str = Field(max_length=300)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
