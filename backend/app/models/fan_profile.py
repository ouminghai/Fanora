"""Persisted fan-profile analysis runs."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.base import new_id, utc_now


class FanProfileRun(SQLModel, table=True):
    __tablename__ = "fan_profile_runs"  # pyright: ignore[reportAssignmentType]

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str | None = Field(default=None, foreign_key="users.id", index=True)
    wallet_address: str = Field(max_length=42, index=True)
    community_id: str = Field(default="global", max_length=100, index=True)
    input_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    output_payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    analysis_source: str = Field(max_length=20, index=True)
    rule_version: str = Field(default="fan-profile-v2", max_length=50)
    prompt_version: str = Field(default="fan-profile-prompt-v2", max_length=50)
    model_id: str = Field(default="rules", max_length=100)
    degraded: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=utc_now)
