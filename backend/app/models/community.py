"""Official-community content, task, check-in, and Fan Token facts."""

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, CheckConstraint, Column, UniqueConstraint
from sqlmodel import Field, SQLModel

from app.models.base import new_id, utc_now


class CommunityPost(SQLModel, table=True):
    __tablename__ = "community_posts"  # pyright: ignore[reportAssignmentType]

    id: str = Field(default_factory=new_id, primary_key=True)
    community_id: str = Field(foreign_key="communities.id", index=True)
    author_user_id: str = Field(foreign_key="users.id", index=True)
    title: str = Field(max_length=120, index=True)
    body: str = Field(max_length=10_000)
    cover_url: str | None = Field(default=None, max_length=1_500_000)
    category: str = Field(default="discussion", max_length=30, index=True)
    status: str = Field(default="published", max_length=20, index=True)
    reply_count: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now)


class CommunityReply(SQLModel, table=True):
    __tablename__ = "community_replies"  # pyright: ignore[reportAssignmentType]

    id: str = Field(default_factory=new_id, primary_key=True)
    post_id: str = Field(foreign_key="community_posts.id", index=True)
    author_user_id: str = Field(foreign_key="users.id", index=True)
    parent_reply_id: str | None = Field(default=None, foreign_key="community_replies.id", index=True)
    body: str = Field(max_length=2000)
    status: str = Field(default="published", max_length=20, index=True)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now)


class CommunityPostReaction(SQLModel, table=True):
    __tablename__ = "community_post_reactions"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_community_post_reaction_user"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    post_id: str = Field(foreign_key="community_posts.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    liked: bool = Field(default=False, index=True)
    bookmarked: bool = Field(default=False, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class CommunityReplyLike(SQLModel, table=True):
    __tablename__ = "community_reply_likes"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("reply_id", "user_id", name="uq_community_reply_like_user"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    reply_id: str = Field(foreign_key="community_replies.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=utc_now)


class FanTask(SQLModel, table=True):
    __tablename__ = "fan_tasks"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        CheckConstraint("reward_fan_tokens > 0", name="ck_fan_tasks_positive_reward"),
        CheckConstraint(
            "participation_limit IS NULL OR participation_limit > 0",
            name="ck_fan_tasks_participation_limit",
        ),
    )

    id: str = Field(default_factory=new_id, primary_key=True)
    community_id: str = Field(foreign_key="communities.id", index=True)
    created_by_user_id: str = Field(foreign_key="users.id", index=True)
    title: str = Field(max_length=120, index=True)
    description: str = Field(max_length=2000)
    task_type: str = Field(default="post_reply", max_length=30, index=True)
    status: str = Field(default="draft", max_length=20, index=True)
    start_at: datetime | None = Field(default=None, index=True)
    end_at: datetime | None = Field(default=None, index=True)
    reward_fan_tokens: int
    target_post_id: str | None = Field(default=None, foreign_key="community_posts.id", index=True)
    validation_rule: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    participation_limit: int | None = Field(default=None)
    created_at: datetime = Field(default_factory=utc_now, index=True)
    updated_at: datetime = Field(default_factory=utc_now)
    published_at: datetime | None = Field(default=None)


class TaskParticipation(SQLModel, table=True):
    __tablename__ = "task_participations"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("task_id", "user_id", name="uq_task_participation_user"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    task_id: str = Field(foreign_key="fan_tasks.id", index=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    status: str = Field(default="claimed", max_length=20, index=True)
    reward_snapshot: int
    reply_id: str | None = Field(default=None, foreign_key="community_replies.id", index=True)
    claimed_at: datetime = Field(default_factory=utc_now)
    submitted_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)


class TaskAuditLog(SQLModel, table=True):
    __tablename__ = "task_audit_logs"  # pyright: ignore[reportAssignmentType]

    id: str = Field(default_factory=new_id, primary_key=True)
    task_id: str = Field(foreign_key="fan_tasks.id", index=True)
    participation_id: str | None = Field(default=None, foreign_key="task_participations.id", index=True)
    actor_user_id: str = Field(foreign_key="users.id", index=True)
    event: str = Field(max_length=40, index=True)
    from_status: str | None = Field(default=None, max_length=20)
    to_status: str = Field(max_length=20)
    detail: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utc_now, index=True)


class DailyCheckIn(SQLModel, table=True):
    __tablename__ = "daily_check_ins"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (UniqueConstraint("user_id", "check_in_date", name="uq_daily_check_in_user_date"),)

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    check_in_date: date = Field(index=True)
    streak_days: int = Field(default=1, ge=1)
    reward_fan_tokens: int = Field(gt=0)
    created_at: datetime = Field(default_factory=utc_now, index=True)


class FanTokenLedger(SQLModel, table=True):
    __tablename__ = "fan_token_ledger"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_fan_token_ledger_idempotency_key"),
        CheckConstraint("delta <> 0", name="ck_fan_token_ledger_nonzero_delta"),
        CheckConstraint("balance_after >= 0", name="ck_fan_token_ledger_nonnegative_balance"),
    )

    id: str = Field(default_factory=new_id, primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    delta: int
    balance_after: int = Field(ge=0)
    source_type: str = Field(max_length=40, index=True)
    source_id: str | None = Field(default=None, max_length=100, index=True)
    task_id: str | None = Field(default=None, foreign_key="fan_tasks.id", index=True)
    idempotency_key: str = Field(max_length=160, unique=True, index=True)
    description: str = Field(max_length=300)
    created_at: datetime = Field(default_factory=utc_now, index=True)
