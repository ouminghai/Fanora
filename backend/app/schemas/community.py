"""Schemas for the single official community and its off-chain activity."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.schemas.auth import validate_image_url


def validate_image_urls(value: list[str]) -> list[str]:
    if len(value) > 6:
        raise ValueError("A maximum of 6 images is allowed")
    return [validate_image_url(item, label="Image") for item in value]


class AuthorSummary(BaseModel):
    id: str
    display_name: str
    avatar_url: str | None
    level: str


class OfficialCommunityResponse(BaseModel):
    id: str
    slug: str
    name: str
    description: str
    logo_url: str
    joined: bool
    member_count: int
    post_count: int


class OfficialCommunityUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=10, max_length=500)
    logo_url: str = Field(min_length=1, max_length=2048)


class PostCreate(BaseModel):
    title: str = Field(min_length=4, max_length=120)
    body: str = Field(min_length=10, max_length=10_000)
    category: Literal["discussion", "music", "story", "creation"] = "discussion"
    cover_url: str | None = None
    image_urls: list[str] = Field(default_factory=list)

    @field_validator("title", "body")
    @classmethod
    def clean_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("cover_url")
    @classmethod
    def validate_cover(cls, value: str | None) -> str | None:
        return validate_image_url(value, label="Cover image")

    @field_validator("image_urls")
    @classmethod
    def validate_images(cls, value: list[str]) -> list[str]:
        return validate_image_urls(value)


class ReplyCreate(BaseModel):
    body: str = Field(min_length=10, max_length=2000)
    parent_reply_id: str | None = None
    image_urls: list[str] = Field(default_factory=list)

    @field_validator("body")
    @classmethod
    def clean_body(cls, value: str) -> str:
        return value.strip()

    @field_validator("image_urls")
    @classmethod
    def validate_images(cls, value: list[str]) -> list[str]:
        return validate_image_urls(value)


class ReplyResponse(BaseModel):
    id: str
    post_id: str
    author: AuthorSummary
    body: str
    image_urls: list[str]
    parent_reply_id: str | None
    like_count: int
    liked: bool
    children: list["ReplyResponse"] = Field(default_factory=list)
    created_at: datetime


class PostSummaryResponse(BaseModel):
    id: str
    title: str
    body_preview: str
    cover_url: str | None
    image_urls: list[str]
    category: str
    reply_count: int
    like_count: int
    bookmark_count: int
    liked: bool
    bookmarked: bool
    author: AuthorSummary
    created_at: datetime
    updated_at: datetime


class PostDetailResponse(BaseModel):
    id: str
    title: str
    body: str
    cover_url: str | None
    image_urls: list[str]
    category: str
    reply_count: int
    like_count: int
    bookmark_count: int
    liked: bool
    bookmarked: bool
    author: AuthorSummary
    replies: list[ReplyResponse]
    has_more_replies: bool = False
    next_replies_offset: int | None = None
    created_at: datetime
    updated_at: datetime


class TaskPresentation(BaseModel):
    catalog_key: str | None = Field(default=None, max_length=80)
    image_url: str | None = Field(default=None, max_length=1_500_000)
    category: str = Field(default="community", min_length=2, max_length=40)
    interaction_prompt: str = Field(default="参与一次真实粉丝互动", min_length=4, max_length=180)
    action_url: str = Field(default="/community/tasks", min_length=1, max_length=500)
    action_label: str = Field(default="开始任务", min_length=2, max_length=40)
    badge_label: str | None = Field(default=None, max_length=60)
    special: bool = False


class TaskCreate(BaseModel):
    title: str = Field(min_length=4, max_length=120)
    description: str = Field(min_length=10, max_length=2000)
    task_type: Literal[
        "post_reply",
        "daily_check_in",
        "content_publish",
        "page_action",
        "streak",
        "event_check_in",
        "future",
    ] = "post_reply"
    start_at: datetime | None = None
    end_at: datetime | None = None
    reward_fan_tokens: int = Field(gt=0, le=100_000)
    target_post_id: str | None = None
    minimum_reply_length: int = Field(default=10, ge=10, le=500)
    content_categories: list[str] = Field(default_factory=list, max_length=8)
    presentation: TaskPresentation = Field(default_factory=TaskPresentation)
    participation_limit: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_window(self) -> "TaskCreate":
        if self.start_at and self.end_at and self.end_at <= self.start_at:
            raise ValueError("Task end time must be later than start time")
        if self.task_type == "post_reply" and not self.target_post_id:
            raise ValueError("Post reply tasks require a target post")
        return self


class TaskUpdate(TaskCreate):
    pass


class TaskStatusUpdate(BaseModel):
    status: Literal["published", "paused", "ended"]


class TaskPageCompletion(BaseModel):
    interaction_note: str = Field(min_length=10, max_length=300)
    image_urls: list[str] = Field(default_factory=list)

    @field_validator("image_urls")
    @classmethod
    def validate_images(cls, value: list[str]) -> list[str]:
        return validate_image_urls(value)


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    task_type: str
    status: str
    start_at: datetime | None
    end_at: datetime | None
    reward_fan_tokens: int
    target_post_id: str | None
    target_post_title: str | None
    required_tag: str | None
    presentation: TaskPresentation
    participation_limit: int | None
    participant_count: int
    participation_status: str | None
    eligible: bool
    unavailable_reason: str | None
    created_at: datetime
    updated_at: datetime


class CheckInRecordResponse(BaseModel):
    check_in_date: date
    reward_fan_tokens: int


class CheckInResponse(BaseModel):
    check_in_date: date
    checked_in: bool
    already_checked_in: bool
    streak_days: int
    reward_fan_tokens: int
    fan_token_balance: int
    month: str
    monthly_records: list[CheckInRecordResponse]
    monthly_reward_fan_tokens: int


class FanTokenLedgerResponse(BaseModel):
    id: str
    delta: int
    balance_after: int
    source_type: str
    source_id: str | None
    task_id: str | None
    description: str
    created_at: datetime


class FanTokenAdjustmentCreate(BaseModel):
    user_id: str
    delta: int = Field(ge=-100_000, le=100_000)
    reason: str = Field(min_length=5, max_length=300)
    operation_id: str = Field(min_length=8, max_length=80)

    @field_validator("delta")
    @classmethod
    def nonzero_delta(cls, value: int) -> int:
        if value == 0:
            raise ValueError("Adjustment delta cannot be zero")
        return value


class RoleGrantResponse(BaseModel):
    user_id: str
    roles: list[str]


class PostEngagementResponse(BaseModel):
    post_id: str
    liked: bool
    bookmarked: bool
    like_count: int
    bookmark_count: int


class ReplyEngagementResponse(BaseModel):
    reply_id: str
    liked: bool
    like_count: int
