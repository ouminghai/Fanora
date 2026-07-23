"""Off-chain fan tasks, daily check-ins, and deterministic completion."""

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from app.api.routes.community import get_official_community, require_creator
from app.core.database import get_database_session
from app.core.security import get_current_identity, get_optional_identity, require_official_member
from app.models.base import utc_now
from app.models.community import DailyCheckIn, FanTask, TaskAuditLog, TaskContentReview, TaskParticipation
from app.models.nft import ChainOperation, CollectibleOwnership, CollectibleTokenType, TaskNftReward
from app.models.user import CommunityMember, UserProfile
from app.schemas.community import (
    CheckInRecordResponse,
    CheckInResponse,
    TaskCreate,
    TaskPageCompletion,
    TaskPresentation,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services.auth import as_utc
from app.services.fan_tokens import fan_token_service
from app.services.identity import AuthenticatedIdentity
from app.services.nft import nft_service
from app.services.task_completion import TaskCompletionEvent, complete_claimed_tasks

task_router = APIRouter(prefix="/tasks")
check_in_router = APIRouter(prefix="/check-ins")


def task_presentation(task: FanTask) -> TaskPresentation:
    raw = task.validation_rule.get("presentation", {})
    fallback_url = f"/community/posts/{task.target_post_id}" if task.target_post_id else "/community/tasks"
    return TaskPresentation.model_validate(
        {
            "catalog_key": task.id,
            "action_url": fallback_url,
            "action_label": "去互动",
            **raw,
        }
    )


def task_is_active(task: FanTask) -> tuple[bool, str | None]:
    now = utc_now()
    if task.status != "published":
        return False, "任务当前不可参与"
    if task.start_at and as_utc(task.start_at) > now:
        return False, "任务尚未开始"
    if task.end_at and as_utc(task.end_at) < now:
        return False, "任务已经结束"
    return True, None


async def to_task_response(
    session: AsyncSession,
    task: FanTask,
    *,
    user_id: str | None,
    is_official_member: bool,
    joined: bool,
) -> TaskResponse:
    participation = None
    if user_id is not None:
        participation = (
            await session.execute(
                select(TaskParticipation).where(
                    TaskParticipation.task_id == task.id,
                    TaskParticipation.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
    participant_count = (
        await session.execute(
            select(func.count(col(TaskParticipation.id))).where(TaskParticipation.task_id == task.id)
        )
    ).scalar_one()
    target_title = None
    if task.target_post_id:
        from app.models.community import CommunityPost

        target_post = await session.get(CommunityPost, task.target_post_id)
        target_title = target_post.title if target_post else None
    active, reason = task_is_active(task)
    eligible = active and is_official_member and joined and participation is None
    if participation is not None:
        reason = "任务已完成" if participation.status == "rewarded" else "任务已领取"
    elif not active:
        pass
    elif not is_official_member:
        reason = "正式入会后可参与"
    elif not joined:
        reason = "请先加入链上社区"
    elif task.participation_limit is not None and participant_count >= task.participation_limit:
        eligible = False
        reason = "任务名额已满"
    review = None
    nft_reward = None
    nft_operation = None
    nft_token_type = None
    if participation is not None:
        review = (
            (
                await session.execute(
                    select(TaskContentReview)
                    .where(TaskContentReview.participation_id == participation.id)
                    .order_by(col(TaskContentReview.created_at).desc())
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
        nft_reward = (
            (
                await session.execute(
                    select(TaskNftReward)
                    .where(TaskNftReward.participation_id == participation.id)
                    .order_by(col(TaskNftReward.reward_version).desc())
                    .limit(1)
                )
            )
            .scalars()
            .first()
        )
        if nft_reward and nft_reward.token_type_id:
            nft_token_type = await session.get(CollectibleTokenType, nft_reward.token_type_id)
        if nft_reward and nft_reward.ownership_id:
            ownership = await session.get(CollectibleOwnership, nft_reward.ownership_id)
            if ownership and ownership.chain_operation_id:
                nft_operation = await session.get(ChainOperation, ownership.chain_operation_id)
    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        task_type=task.task_type,
        status=task.status,
        start_at=task.start_at,
        end_at=task.end_at,
        reward_fan_tokens=task.reward_fan_tokens,
        target_post_id=task.target_post_id,
        target_post_title=target_title,
        required_tag=task.validation_rule.get("required_tag") or f"#{task.title}",
        presentation=task_presentation(task),
        participation_limit=task.participation_limit,
        participant_count=participant_count,
        participation_status=participation.status if participation else None,
        review_decision=review.decision if review else None,
        review_quality_score=review.quality_score if review else None,
        review_reasons=review.reasons if review else [],
        nft_reward_status=nft_reward.status if nft_reward else None,
        nft_transaction_hash=nft_operation.transaction_hash if nft_operation else None,
        nft_explorer_url=(
            f"https://testnet.monadvision.com/nft/{nft_token_type.contract_address}/{nft_token_type.token_id}?tab=Overview"
            if nft_token_type
            else None
        ),
        eligible=eligible,
        unavailable_reason=reason,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


async def user_task_context(session: AsyncSession, identity: AuthenticatedIdentity) -> tuple[bool, bool]:
    profile = await session.get(UserProfile, identity.user_id)
    community = await get_official_community(session)
    joined = (
        await session.execute(
            select(CommunityMember.id).where(
                CommunityMember.community_id == community.id,
                CommunityMember.user_id == identity.user_id,
            )
        )
    ).scalar_one_or_none() is not None
    return bool(profile and profile.is_official_member), joined


@task_router.get("", response_model=list[TaskResponse])
async def list_tasks(
    identity: AuthenticatedIdentity | None = Depends(get_optional_identity),
    session: AsyncSession = Depends(get_database_session),
) -> list[TaskResponse]:
    community = await get_official_community(session)
    tasks = list(
        (
            await session.execute(
                select(FanTask)
                .where(FanTask.community_id == community.id, FanTask.status != "draft")
                .order_by(col(FanTask.created_at).desc())
            )
        )
        .scalars()
        .all()
    )
    is_member, joined = (False, False)
    if identity is not None:
        is_member, joined = await user_task_context(session, identity)
    return [
        await to_task_response(
            session,
            task,
            user_id=identity.user_id if identity else None,
            is_official_member=is_member,
            joined=joined,
        )
        for task in tasks
    ]


@task_router.post("/{task_id}/claim", response_model=TaskResponse)
async def claim_task(
    task_id: str,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> TaskResponse:
    task = await session.get(FanTask, task_id, with_for_update=True)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    active, reason = task_is_active(task)
    if not active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=reason)
    _, joined = await user_task_context(session, identity)
    if not joined:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Join the official community first")
    existing = (
        await session.execute(
            select(TaskParticipation).where(
                TaskParticipation.task_id == task.id,
                TaskParticipation.user_id == identity.user_id,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        if task.participation_limit is not None:
            count = (
                await session.execute(
                    select(func.count(col(TaskParticipation.id))).where(TaskParticipation.task_id == task.id)
                )
            ).scalar_one()
            if count >= task.participation_limit:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Task participation limit reached")
        try:
            existing = TaskParticipation(
                task_id=task.id,
                user_id=identity.user_id,
                reward_snapshot=task.reward_fan_tokens,
            )
            session.add(existing)
            await session.flush()
            session.add(
                TaskAuditLog(
                    task_id=task.id,
                    participation_id=existing.id,
                    actor_user_id=identity.user_id,
                    event="claimed",
                    to_status="claimed",
                )
            )
            await session.commit()
        except IntegrityError:
            await session.rollback()
            task = await session.get(FanTask, task_id)
            if task is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found") from None
    if task.task_type == "daily_check_in":
        local_date = utc_now().astimezone(ZoneInfo("Asia/Shanghai")).date()
        checked_in = (
            await session.execute(
                select(DailyCheckIn.id).where(
                    DailyCheckIn.user_id == identity.user_id,
                    DailyCheckIn.check_in_date == local_date,
                )
            )
        ).scalar_one_or_none()
        if checked_in is not None:
            await complete_claimed_tasks(
                session,
                user_id=identity.user_id,
                event=TaskCompletionEvent(
                    task_type="daily_check_in",
                    source_id=local_date.isoformat(),
                    detail="The member had already completed today's official community check-in.",
                    award_tokens=False,
                ),
            )
            await session.commit()
    return await to_task_response(
        session,
        task,
        user_id=identity.user_id,
        is_official_member=True,
        joined=True,
    )


@task_router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_page_task(
    task_id: str,
    payload: TaskPageCompletion,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> TaskResponse:
    task = await session.get(FanTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.task_type != "page_action":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This task is completed by its configured community interaction",
        )
    active, reason = task_is_active(task)
    if not active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=reason)
    _, joined = await user_task_context(session, identity)
    if not joined:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Join the official community first")
    participation = (
        await session.execute(
            select(TaskParticipation).where(
                TaskParticipation.task_id == task.id,
                TaskParticipation.user_id == identity.user_id,
            )
        )
    ).scalar_one_or_none()
    if participation is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Claim the task before completing it")
    if participation.status == "claimed":
        participation.submission = {
            "body": payload.interaction_note,
            "image_urls": payload.image_urls,
        }
        completed = await complete_claimed_tasks(
            session,
            user_id=identity.user_id,
            event=TaskCompletionEvent(
                task_type="page_action",
                task_id=task.id,
                source_id=task.id,
                content_text=payload.interaction_note,
                detail=f"Event-page memory: {payload.interaction_note}",
            ),
        )
        if completed:
            await nft_service.mint_task_reward(
                session,
                task=task,
                participation=participation,
                user_id=identity.user_id,
            )
        else:
            await session.commit()
    return await to_task_response(
        session,
        task,
        user_id=identity.user_id,
        is_official_member=True,
        joined=True,
    )


@task_router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreate,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> TaskResponse:
    await require_creator(session, identity.user_id)
    community = await get_official_community(session)
    from app.models.community import CommunityPost

    if payload.target_post_id:
        post = await session.get(CommunityPost, payload.target_post_id)
        if post is None or post.community_id != community.id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Target post not found")
    values = payload.model_dump(exclude={"minimum_reply_length", "content_categories", "presentation"})
    task = FanTask(
        community_id=community.id,
        created_by_user_id=identity.user_id,
        validation_rule={
            "minimum_reply_length": payload.minimum_reply_length,
            "content_categories": payload.content_categories,
            "presentation": payload.presentation.model_dump(),
        },
        **values,
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return await to_task_response(session, task, user_id=identity.user_id, is_official_member=True, joined=True)


@task_router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    payload: TaskUpdate,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> TaskResponse:
    await require_creator(session, identity.user_id)
    task = await session.get(FanTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.status not in {"draft", "paused"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only draft or paused tasks can be edited")
    if payload.target_post_id:
        from app.models.community import CommunityPost

        post = await session.get(CommunityPost, payload.target_post_id)
        if post is None or post.community_id != task.community_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Target post not found")
    for field, value in payload.model_dump(
        exclude={"minimum_reply_length", "content_categories", "presentation"}
    ).items():
        setattr(task, field, value)
    task.validation_rule = {
        "minimum_reply_length": payload.minimum_reply_length,
        "content_categories": payload.content_categories,
        "presentation": payload.presentation.model_dump(),
    }
    task.updated_at = utc_now()
    await session.commit()
    return await to_task_response(session, task, user_id=identity.user_id, is_official_member=True, joined=True)


@task_router.post("/{task_id}/status", response_model=TaskResponse)
async def change_task_status(
    task_id: str,
    payload: TaskStatusUpdate,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> TaskResponse:
    await require_creator(session, identity.user_id)
    task = await session.get(FanTask, task_id)
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    transitions = {
        "draft": {"published"},
        "published": {"paused", "ended"},
        "paused": {"published", "ended"},
        "ended": set(),
    }
    if payload.status not in transitions.get(task.status, set()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid task status transition")
    previous = task.status
    task.status = payload.status
    task.updated_at = utc_now()
    if payload.status == "published" and task.published_at is None:
        task.published_at = utc_now()
    session.add(
        TaskAuditLog(
            task_id=task.id,
            actor_user_id=identity.user_id,
            event="status_changed",
            from_status=previous,
            to_status=payload.status,
        )
    )
    await session.commit()
    return await to_task_response(session, task, user_id=identity.user_id, is_official_member=True, joined=True)


async def build_check_in_response(
    session: AsyncSession,
    *,
    user_id: str,
    local_date: date,
    already_checked_in: bool,
) -> CheckInResponse:
    month_start = local_date.replace(day=1)
    next_month = (
        date(month_start.year + 1, 1, 1)
        if month_start.month == 12
        else date(month_start.year, month_start.month + 1, 1)
    )
    monthly_records = list(
        (
            await session.execute(
                select(DailyCheckIn)
                .where(
                    DailyCheckIn.user_id == user_id,
                    DailyCheckIn.check_in_date >= month_start,
                    DailyCheckIn.check_in_date < next_month,
                )
                .order_by(col(DailyCheckIn.check_in_date))
            )
        )
        .scalars()
        .all()
    )
    today_record = next((record for record in monthly_records if record.check_in_date == local_date), None)
    profile = await session.get(UserProfile, user_id)
    return CheckInResponse(
        check_in_date=local_date,
        checked_in=today_record is not None,
        already_checked_in=already_checked_in,
        streak_days=today_record.streak_days if today_record else 0,
        reward_fan_tokens=today_record.reward_fan_tokens if today_record else 20,
        fan_token_balance=profile.fan_token_balance if profile else 0,
        month=month_start.strftime("%Y-%m"),
        monthly_records=[
            CheckInRecordResponse(
                check_in_date=record.check_in_date,
                reward_fan_tokens=record.reward_fan_tokens,
            )
            for record in monthly_records
        ],
        monthly_reward_fan_tokens=sum(record.reward_fan_tokens for record in monthly_records),
    )


@check_in_router.get("/me", response_model=CheckInResponse)
async def get_today_check_in(
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> CheckInResponse:
    local_date = utc_now().astimezone(ZoneInfo("Asia/Shanghai")).date()
    existing = (
        await session.execute(
            select(DailyCheckIn.id).where(
                DailyCheckIn.user_id == identity.user_id,
                DailyCheckIn.check_in_date == local_date,
            )
        )
    ).scalar_one_or_none()
    return await build_check_in_response(
        session,
        user_id=identity.user_id,
        local_date=local_date,
        already_checked_in=existing is not None,
    )


@check_in_router.post("", response_model=CheckInResponse)
async def check_in(
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> CheckInResponse:
    local_date = utc_now().astimezone(ZoneInfo("Asia/Shanghai")).date()
    existing = (
        await session.execute(
            select(DailyCheckIn).where(
                DailyCheckIn.user_id == identity.user_id,
                DailyCheckIn.check_in_date == local_date,
            )
        )
    ).scalar_one_or_none()
    profile = await session.get(UserProfile, identity.user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found")
    if existing is not None:
        completed = await complete_claimed_tasks(
            session,
            user_id=identity.user_id,
            event=TaskCompletionEvent(
                task_type="daily_check_in",
                source_id=local_date.isoformat(),
                detail="The member completed today's official community check-in.",
                award_tokens=False,
            ),
        )
        if completed:
            await session.commit()
            await session.refresh(profile)
        return await build_check_in_response(
            session,
            user_id=identity.user_id,
            local_date=local_date,
            already_checked_in=True,
        )
    yesterday = local_date - timedelta(days=1)
    previous = (
        await session.execute(
            select(DailyCheckIn).where(
                DailyCheckIn.user_id == identity.user_id,
                DailyCheckIn.check_in_date == yesterday,
            )
        )
    ).scalar_one_or_none()
    streak = (previous.streak_days + 1) if previous else 1
    entry = await fan_token_service.award_rule(
        session,
        user_id=identity.user_id,
        rule_code="daily-check-in",
        source_id=local_date.isoformat(),
        idempotency_key=f"daily-check-in:{identity.user_id}:{local_date.isoformat()}",
        fallback_delta=20,
        fallback_description="每日签到",
    )
    reward = entry.delta if entry else 20
    check_in_record = DailyCheckIn(
        user_id=identity.user_id,
        check_in_date=local_date,
        streak_days=streak,
        reward_fan_tokens=reward,
    )
    session.add(check_in_record)
    if streak % 7 == 0:
        await fan_token_service.award_rule(
            session,
            user_id=identity.user_id,
            rule_code="seven-day-streak",
            source_id=local_date.isoformat(),
            idempotency_key=f"seven-day-streak:{identity.user_id}:{local_date.isoformat()}",
            fallback_delta=100,
            fallback_description="连续签到 7 天",
        )
    await complete_claimed_tasks(
        session,
        user_id=identity.user_id,
        event=TaskCompletionEvent(
            task_type="daily_check_in",
            source_id=local_date.isoformat(),
            detail="The member completed today's official community check-in.",
            award_tokens=False,
        ),
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return await get_today_check_in(identity, session)
    await session.refresh(profile)
    return await build_check_in_response(
        session,
        user_id=identity.user_id,
        local_date=local_date,
        already_checked_in=False,
    )
