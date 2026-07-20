"""Membership level and paid official membership API schemas."""

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

TRANSACTION_HASH_PATTERN = re.compile(r"^0x[a-fA-F0-9]{64}$")


class MembershipLevelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    description: str
    rank: int
    min_token_balance: int | None
    max_token_balance: int | None
    badge_image_url: str
    is_management: bool


class OfficialMembershipStatusResponse(BaseModel):
    status: str
    is_official_member: bool
    fee_mon: str
    fee_wei: str
    treasury_address: str | None
    chain_id: int
    transaction_hash: str | None = None
    joined_at: datetime | None = None


class OfficialMembershipVerifyRequest(BaseModel):
    transaction_hash: str

    @field_validator("transaction_hash")
    @classmethod
    def validate_transaction_hash(cls, value: str) -> str:
        if not TRANSACTION_HASH_PATTERN.fullmatch(value):
            raise ValueError("Invalid EVM transaction hash")
        return value.lower()
