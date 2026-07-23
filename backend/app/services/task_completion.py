"""Quest completion orchestration with Agent review and deterministic rewards."""

from dataclasses import dataclass
from typing import Literal, cast

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.agents.content_review import content_review_agent
from app.models.base import utc_now
from app.models.community import FanTask, TaskAuditLog, TaskContentReview, TaskParticipation
from app.schemas.content_review import ContentReviewRequest, ContentReviewResult
from app.services.auth import as_utc
from app.services.fan_tokens import fan_token_service


@dataclass(frozen=True, slots=True)
class TaskCompletionEvent:
    task_type: str
    source_id: str
    detail: str
    task_id: str | None = None
    target_post_id: str | None = None
    reply_id: str | None = None
    reply_length: int | None = None
    content_category: str | None = None
    content_title: str | None = None
    content_text: str | None = None
    award_tokens: bool = True


def _matches(task: FanTask, event: TaskCompletionEvent) -> bool:
    if event.task_id is not None and task.id != event.task_id:
        return False
    if event.target_post_id is not None and task.target_post_id != event.target_post_id:
        return False
    requires_review = task.task_type in {"content_publish", "post_reply", "page_action"}
    if event.reply_length is not None and not requires_review:
        minimum_length = int(task.validation_rule.get("minimum_reply_length", 10))
        if event.reply_length < minimum_length:
            return False
    allowed_categories = task.validation_rule.get("content_categories", [])
    if allowed_categories and event.content_category not in allowed_categories:
        return False
    required_tag = (
        (task.validation_rule.get("required_tag") or f"#{task.title}") if task.task_type == "content_publish" else None
    )
    if (
        required_tag
        and not requires_review
        and (event.content_text is None or required_tag.casefold() not in event.content_text.casefold())
    ):
        return False
    return True


def _requires_agent_review(task: FanTask) -> bool:
    return task.task_type in {"content_publish", "post_reply", "page_action"}


async def _review_submission(
    session: AsyncSession,
    *,
    task: FanTask,
    participation: TaskParticipation,
    user_id: str,
    event: TaskCompletionEvent,
) -> ContentReviewResult:
    presentation = task.validation_rule.get("presentation", {})
    interaction_prompt = presentation.get("interaction_prompt", "") if isinstance(presentation, dict) else ""
    required_tag = (
        task.validation_rule.get("required_tag") or f"#{task.title}" if task.task_type == "content_publish" else None
    )
    minimum_length = int(
        task.validation_rule.get(
            "minimum_reply_length" if task.task_type == "post_reply" else "minimum_content_length",
            10,
        )
    )
    content_type = cast(
        Literal["post", "reply", "page_action"],
        {
            "content_publish": "post",
            "post_reply": "reply",
            "page_action": "page_action",
        }[task.task_type],
    )
    review = await content_review_agent.review(
        ContentReviewRequest(
            task_id=task.id,
            task_title=task.title,
            task_description=task.description,
            interaction_prompt=interaction_prompt,
            content_type=content_type,
            source_id=event.source_id,
            title=event.content_title or "",
            body=event.content_text or "",
            category=event.content_category,
            required_tag=required_tag,
            minimum_length=minimum_length,
        )
    )
    session.add(
        TaskContentReview(
            task_id=task.id,
            participation_id=participation.id,
            user_id=user_id,
            source_type=event.task_type,
            source_id=event.source_id,
            decision=review.decision,
            quality_score=review.quality_score,
            signals={
                "tag_present": review.tag_present,
                "relevant": review.relevant,
                "spam": review.spam,
                "meaningful": review.meaningful,
                "policy_safe": review.policy_safe,
                "ai_generated_likelihood": review.ai_generated_likelihood,
            },
            reasons=review.reasons,
            review_source=review.source,
            model_id=review.model_id,
            rule_version=review.rule_version,
            prompt_version=review.prompt_version,
            degraded=review.degraded,
        )
    )
    return review


async def complete_claimed_tasks(
    session: AsyncSession,
    *,
    user_id: str,
    event: TaskCompletionEvent,
) -> int:
    """Complete every claimed task matched by one verified interaction event."""

    now = utc_now()
    rows = list(
        (
            await session.execute(
                select(TaskParticipation, FanTask)
                .join(FanTask, col(FanTask.id) == col(TaskParticipation.task_id))
                .where(
                    TaskParticipation.user_id == user_id,
                    TaskParticipation.status == "claimed",
                    FanTask.task_type == event.task_type,
                    FanTask.status == "published",
                )
            )
        ).all()
    )
    completed = 0
    for participation, task in rows:
        if task.start_at and as_utc(task.start_at) > now:
            continue
        if task.end_at and as_utc(task.end_at) < now:
            continue
        if not _matches(task, event):
            continue
        if _requires_agent_review(task):
            review = await _review_submission(
                session,
                task=task,
                participation=participation,
                user_id=user_id,
                event=event,
            )
            if review.decision != "approved":
                session.add(
                    TaskAuditLog(
                        task_id=task.id,
                        participation_id=participation.id,
                        actor_user_id=user_id,
                        event=f"agent_review_{review.decision}",
                        from_status="claimed",
                        to_status="claimed",
                        detail="; ".join(review.reasons)[:500],
                    )
                )
                continue
        participation.status = "rewarded"
        participation.reply_id = event.reply_id
        participation.submitted_at = now
        participation.completed_at = now
        session.add(
            TaskAuditLog(
                task_id=task.id,
                participation_id=participation.id,
                actor_user_id=user_id,
                event="verified_and_rewarded",
                from_status="claimed",
                to_status="rewarded",
                detail=event.detail,
            )
        )
        if event.award_tokens:
            await fan_token_service.award(
                session,
                user_id=user_id,
                delta=participation.reward_snapshot,
                source_type="task",
                source_id=participation.id,
                task_id=task.id,
                idempotency_key=f"task-reward:{task.id}:{user_id}",
                description=f"完成任务：{task.title}",
            )
        completed += 1
    return completed
