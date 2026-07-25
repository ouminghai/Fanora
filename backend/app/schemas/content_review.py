"""Structured input and output for task-content quality review."""

from typing import Literal

from pydantic import BaseModel, Field

ReviewDecision = Literal["approved", "rejected", "manual_review"]


class ContentReviewRequest(BaseModel):
    task_id: str
    task_title: str = Field(min_length=1, max_length=120)
    task_description: str = Field(default="", max_length=2000)
    interaction_prompt: str = Field(default="", max_length=500)
    content_type: Literal["post", "reply", "page_action"]
    source_id: str
    title: str = Field(default="", max_length=120)
    body: str = Field(min_length=1, max_length=10_000)
    category: str | None = Field(default=None, max_length=40)
    required_tag: str | None = Field(default=None, max_length=140)
    minimum_length: int = Field(default=4, ge=1, le=2000)


class LlmContentReview(BaseModel):
    decision: ReviewDecision
    quality_score: int = Field(ge=0, le=100)
    relevant: bool
    spam: bool
    meaningful: bool
    policy_safe: bool
    ai_generated_likelihood: Literal["low", "medium", "high"] = "low"
    reasons: list[str] = Field(min_length=1, max_length=6)


class ContentReviewResult(BaseModel):
    decision: ReviewDecision
    quality_score: int = Field(ge=0, le=100)
    tag_present: bool
    relevant: bool
    spam: bool
    meaningful: bool
    policy_safe: bool
    ai_generated_likelihood: Literal["low", "medium", "high"]
    reasons: list[str] = Field(min_length=1, max_length=8)
    source: Literal["rules", "llm"]
    degraded: bool
    rule_version: str = "content-review-v1"
    prompt_version: str = "content-review-prompt-v1"
    model_id: str = "rules"
