"""Unified users, login identities, and wallet records."""

from datetime import datetime

from sqlalchemy import UniqueConstraint
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
