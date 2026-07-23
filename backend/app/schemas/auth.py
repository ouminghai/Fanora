"""Authentication, user profile, and community API schemas."""

import base64
import binascii
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

WALLET_PATTERN = re.compile(r"^0x[a-fA-F0-9]{40}$")
USERNAME_PATTERN = re.compile(r"^[a-z0-9_]{3,40}$")
SLUG_PATTERN = re.compile(r"^[a-z0-9-]{3,60}$")
ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_AVATAR_BYTES = 1024 * 1024


def validate_image_url(value: str | None, *, label: str = "Image", max_bytes: int = MAX_AVATAR_BYTES) -> str | None:
    if value is None or value == "":
        return None
    if value.startswith(("https://", "http://")):
        if len(value) > 2048:
            raise ValueError(f"{label} URL is too long")
        return value
    if value.startswith("data:image/"):
        try:
            header, encoded = value.split(",", 1)
            mime_type = header[5:].split(";", 1)[0]
            if mime_type not in ALLOWED_AVATAR_TYPES or ";base64" not in header:
                raise ValueError
            if len(base64.b64decode(encoded, validate=True)) > max_bytes:
                raise ValueError(f"{label} must be no larger than 1 MB")
        except (ValueError, binascii.Error) as error:
            if str(error) == f"{label} must be no larger than 1 MB":
                raise
            raise ValueError(f"{label} must be a JPEG, PNG, WebP, or GIF image") from error
        return value
    raise ValueError(f"{label} must be an HTTP image URL or uploaded image")


def validate_avatar_url(value: str | None) -> str | None:
    return validate_image_url(value, label="Avatar")


class AuthChallengeRequest(BaseModel):
    wallet_address: str

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, value: str) -> str:
        if not WALLET_PATTERN.fullmatch(value):
            raise ValueError("Invalid EVM wallet address")
        return value


class AuthChallengeResponse(BaseModel):
    challenge_id: str
    message: str
    expires_at: datetime


class WalletLoginRequest(BaseModel):
    challenge_id: str
    wallet_address: str
    signature: str = Field(min_length=130, max_length=132)

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, value: str) -> str:
        if not WALLET_PATTERN.fullmatch(value):
            raise ValueError("Invalid EVM wallet address")
        return value

    @field_validator("signature")
    @classmethod
    def validate_signature(cls, value: str) -> str:
        encoded = value[2:] if value.startswith("0x") else value
        if len(encoded) != 130 or not all(character in "0123456789abcdefABCDEF" for character in encoded):
            raise ValueError("Invalid EVM signature")
        return value


class WalletResponse(BaseModel):
    address: str
    wallet_type: str
    provider: str | None
    is_primary: bool


class CommunitySummary(BaseModel):
    id: str
    slug: str
    name: str
    description: str
    logo_url: str
    owner_user_id: str
    is_public: bool
    joined: bool = False


class UserResponse(BaseModel):
    id: str
    display_name: str | None
    username: str | None
    email: str | None = None
    avatar_url: str | None
    bio: str | None
    locale: str
    level: str
    is_official_member: bool
    official_member_since: datetime | None
    fan_token_balance: int
    fan_token_lifetime_earned: int
    fan_type: str
    profile_visibility: str
    onboarding_completed: bool
    roles: list[str]
    primary_wallet: WalletResponse
    communities: list[CommunitySummary] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AuthSessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    is_new_user: bool
    user: UserResponse


class UserProfileUpdate(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)
    username: str | None = Field(default=None, min_length=3, max_length=40)
    avatar_url: str | None = None
    bio: str | None = Field(default=None, max_length=280)
    locale: str = Field(default="zh-CN", min_length=2, max_length=20)
    profile_visibility: Literal["public", "private"] = "public"

    @field_validator("display_name")
    @classmethod
    def clean_display_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Display name is too short")
        return cleaned

    @field_validator("username")
    @classmethod
    def clean_username(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        cleaned = value.lower().strip()
        if not USERNAME_PATTERN.fullmatch(cleaned):
            raise ValueError("Username may only contain lowercase letters, numbers, and underscores")
        return cleaned

    @field_validator("avatar_url")
    @classmethod
    def validate_avatar(cls, value: str | None) -> str | None:
        return validate_avatar_url(value)


class CommunityCreate(BaseModel):
    slug: str
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=10, max_length=500)
    logo_url: str
    is_public: bool = True

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        cleaned = value.lower().strip()
        if not SLUG_PATTERN.fullmatch(cleaned):
            raise ValueError("Slug may only contain lowercase letters, numbers, and hyphens")
        return cleaned

    @field_validator("logo_url")
    @classmethod
    def validate_logo(cls, value: str) -> str:
        validated = validate_avatar_url(value)
        if validated is None:
            raise ValueError("Community logo is required")
        return validated


class CommunityUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=10, max_length=500)
    logo_url: str
    is_public: bool = True

    @field_validator("logo_url")
    @classmethod
    def validate_logo(cls, value: str) -> str:
        validated = validate_avatar_url(value)
        if validated is None:
            raise ValueError("Community logo is required")
        return validated
