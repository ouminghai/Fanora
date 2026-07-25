"""Unified users, login identities, and wallet records."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import new_id, utc_now


class User(SQLModel, table=True):
    __tablename__ = "users"  # pyright: ignore[reportAssignmentType]

    id: str = Field(default_factory=new_id, primary_key=True)
    display_name: str | None = Field(default=None, max_length=80)
    status: str = Field(default="active", max_length=20, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AuthIdentity(SQLModel, table=True):
    __tablename__ = "auth_identities"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("provider", "subject", name="uq_auth_identity_provider_subject"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    provider: str = Field(max_length=50)
    subject: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=utc_now)


class Wallet(SQLModel, table=True):
    __tablename__ = "wallets"  # pyright: ignore[reportAssignmentType]

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    address: str = Field(max_length=42, unique=True, index=True)
    wallet_type: str = Field(max_length=20)
    provider: str | None = Field(default=None, max_length=50)
    chain_family: str = Field(default="evm", max_length=20)
    is_primary: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class UserProfile(SQLModel, table=True):
    __tablename__ = "user_profiles"  # pyright: ignore[reportAssignmentType]

    user_id: str = Field(foreign_key="users.id", primary_key=True)
    username: str | None = Field(default=None, max_length=40, unique=True, index=True)
    email: str | None = Field(default=None, max_length=320)
    avatar_url: str | None = Field(default=None, max_length=1_500_000)
    bio: str | None = Field(default=None, max_length=280)
    locale: str = Field(default="zh-CN", max_length=20)
    level: str = Field(default="新生儿", max_length=30)
    fan_token_balance: int = Field(default=0, ge=0)
    fan_token_lifetime_earned: int = Field(default=0, ge=0)
    fan_type: str = Field(default="Newcomer", max_length=50)
    profile_visibility: str = Field(default="public", max_length=20)
    onboarding_completed: bool = Field(default=False)
    is_official_member: bool = Field(default=False, index=True)
    official_member_since: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class OfficialMembershipPayment(SQLModel, table=True):
    __tablename__ = "official_membership_payments"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_official_membership_payment_user"),
        UniqueConstraint("transaction_hash", name="uq_official_membership_payment_transaction"),
        CheckConstraint("amount_wei >= 0", name="ck_official_membership_payment_amount_nonnegative"),
    )

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    wallet_address: str = Field(max_length=42, index=True)
    treasury_address: str = Field(max_length=42)
    transaction_hash: str = Field(max_length=66, index=True)
    chain_id: int = Field(index=True)
    amount_wei: int = Field(sa_column=Column(BigInteger, nullable=False))
    block_number: int = Field(sa_column=Column(BigInteger, nullable=False))
    status: str = Field(default="confirmed", max_length=20, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    confirmed_at: datetime = Field(default_factory=utc_now)


class UserRole(SQLModel, table=True):
    __tablename__ = "user_roles"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("user_id", "role", name="uq_user_role"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    role: str = Field(default="fan", max_length=30, index=True)
    created_at: datetime = Field(default_factory=utc_now)


class LoginChallenge(SQLModel, table=True):
    __tablename__ = "login_challenges"  # pyright: ignore[reportAssignmentType]

    id: str = Field(default_factory=new_id, primary_key=True)
    wallet_address: str = Field(max_length=42, index=True)
    message: str = Field(max_length=1000)
    expires_at: datetime = Field(index=True)
    used_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"  # pyright: ignore[reportAssignmentType]

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(max_length=64, unique=True, index=True)
    expires_at: datetime = Field(index=True)
    revoked_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now)


class AuthSecurityEvent(SQLModel, table=True):
    __tablename__ = "auth_security_events"  # pyright: ignore[reportAssignmentType]

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str | None = Field(default=None, foreign_key="users.id", index=True)
    wallet_address: str | None = Field(default=None, max_length=42, index=True)
    event: str = Field(max_length=40, index=True)
    outcome: str = Field(max_length=20, index=True)
    ip_address: str | None = Field(default=None, max_length=64)
    detail: str | None = Field(default=None, max_length=300)
    created_at: datetime = Field(default_factory=utc_now, index=True)


class Community(SQLModel, table=True):
    __tablename__ = "communities"  # pyright: ignore[reportAssignmentType]

    id: str = Field(default_factory=new_id, primary_key=True)
    owner_user_id: str = Field(foreign_key="users.id", index=True)
    slug: str = Field(max_length=60, unique=True, index=True)
    name: str = Field(max_length=80, index=True)
    description: str = Field(max_length=500)
    logo_url: str = Field(max_length=2048)
    is_public: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CommunityMember(SQLModel, table=True):
    __tablename__ = "community_members"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("community_id", "user_id", name="uq_community_member"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    community_id: str = Field(foreign_key="communities.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    role: str = Field(default="member", max_length=30)
    joined_at: datetime = Field(default_factory=utc_now)
