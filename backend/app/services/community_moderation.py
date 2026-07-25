"""Lenient community publishing moderation, separate from Quest verification."""

from typing import Literal

from app.agents.content_review import content_review_agent
from app.schemas.content_review import ContentReviewRequest, ContentReviewResult


async def moderate_community_content(
    *,
    content_type: Literal["post", "reply"],
    source_id: str,
    title: str = "",
    body: str,
    category: str | None = None,
) -> ContentReviewResult:
    return await content_review_agent.review(
        ContentReviewRequest(
            task_id=f"community-{content_type}-moderation",
            task_title="Fanora 社区内容发布",
            task_description="围绕 Fanora 粉丝社区、音乐、演出记忆、粉丝故事、社区共创或相关互动发布内容。",
            interaction_prompt="判断内容是否适合发布到 Fanora 社区；允许简短普通的真实粉丝表达。",
            content_type=content_type,
            source_id=source_id,
            title=title,
            body=body,
            category=category,
            required_tag=None,
            minimum_length=2 if content_type == "reply" else 4,
        )
    )
