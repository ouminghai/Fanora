"""Deterministic completion for the supported fan-task interaction modes."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.models.base import utc_now
from app.models.community import FanTask, TaskAuditLog, TaskParticipation
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
    content_text: str | None = None
    award_tokens: bool = True


def _matches(task: FanTask, event: TaskCompletionEvent) -> bool:
    if event.task_id is not None and task.id != event.task_id:
        return False
    if event.target_post_id is not None and task.target_post_id != event.target_post_id:
        return False
    if event.reply_length is not None:
        minimum_length = int(task.validation_rule.get("minimum_reply_length", 10))
        if event.reply_length < minimum_length:
            return False
    allowed_categories = task.validation_rule.get("content_categories", [])
    if allowed_categories and event.content_category not in allowed_categories:
        return False
    required_tag = (task.validation_rule.get("required_tag") or f"#{task.title}") if task.task_type == "content_publish" else None
    if required_tag and (event.content_text is None or required_tag.casefold() not in event.content_text.casefold()):
        return False
    return True


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
