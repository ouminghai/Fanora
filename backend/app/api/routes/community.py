"""Single official-community content and membership endpoints."""

import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from app.core.database import get_database_session
from app.core.security import get_current_identity, get_optional_identity, require_official_member
from app.models.base import utc_now
from app.models.community import (
    CommunityPost,
    CommunityPostReaction,
    CommunityReply,
    CommunityReplyLike,
)
from app.models.user import Community, CommunityMember, User, UserProfile, UserRole
from app.schemas.community import (
    AuthorSummary,
    OfficialCommunityResponse,
    OfficialCommunityUpdate,
    PostCreate,
    PostDetailResponse,
    PostEngagementResponse,
    PostSummaryResponse,
    ReplyCreate,
    ReplyEngagementResponse,
    ReplyResponse,
)
from app.services.fan_tokens import fan_token_service
from app.services.identity import AuthenticatedIdentity
from app.services.task_completion import TaskCompletionEvent, complete_claimed_tasks

router = APIRouter(prefix="/community")


def markdown_preview(body: str, limit: int = 160) -> str:
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", body)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"(^|\n)\s{0,3}(#{1,6}|>|[-+*]|\d+\.)\s+", r"\1", text)
    text = re.sub(r"[`*_~]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


async def get_official_community(session: AsyncSession) -> Community:
    community = (
        await session.execute(select(Community).where(Community.slug == "fanora-official").limit(1))
    ).scalar_one_or_none()
    if community is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Official community is not configured"
        )
    return community


async def require_creator(session: AsyncSession, user_id: str) -> None:
    role = (
        await session.execute(
            select(UserRole).where(UserRole.user_id == user_id, col(UserRole.role).in_(["creator", "admin"]))
        )
    ).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Creator role required")


async def author_summary(session: AsyncSession, user_id: str) -> AuthorSummary:
    user = await session.get(User, user_id)
    profile = await session.get(UserProfile, user_id)
    if user is None:
        return AuthorSummary(id=user_id, display_name="Fanora 用户", avatar_url=None, level="成员")
    return AuthorSummary(
        id=user_id,
        display_name=user.display_name or "Fanora 用户",
        avatar_url=profile.avatar_url if profile else None,
        level=profile.level if profile and profile.is_official_member else "社区成员",
    )


async def post_engagement(
    session: AsyncSession,
    post_id: str,
    user_id: str | None,
) -> tuple[int, int, bool, bool]:
    like_count = (
        await session.execute(
            select(func.count(col(CommunityPostReaction.id))).where(
                CommunityPostReaction.post_id == post_id,
                col(CommunityPostReaction.liked).is_(True),
            )
        )
    ).scalar_one()
    bookmark_count = (
        await session.execute(
            select(func.count(col(CommunityPostReaction.id))).where(
                CommunityPostReaction.post_id == post_id,
                col(CommunityPostReaction.bookmarked).is_(True),
            )
        )
    ).scalar_one()
    reaction = None
    if user_id:
        reaction = (
            await session.execute(
                select(CommunityPostReaction).where(
                    CommunityPostReaction.post_id == post_id,
                    CommunityPostReaction.user_id == user_id,
                )
            )
        ).scalar_one_or_none()
    return like_count, bookmark_count, bool(reaction and reaction.liked), bool(reaction and reaction.bookmarked)


async def to_reply_response(
    session: AsyncSession,
    reply: CommunityReply,
    *,
    user_id: str | None,
    children: list[ReplyResponse] | None = None,
) -> ReplyResponse:
    like_count = (
        await session.execute(
            select(func.count(col(CommunityReplyLike.id))).where(CommunityReplyLike.reply_id == reply.id)
        )
    ).scalar_one()
    liked = False
    if user_id:
        liked = (
            await session.execute(
                select(CommunityReplyLike.id).where(
                    CommunityReplyLike.reply_id == reply.id,
                    CommunityReplyLike.user_id == user_id,
                )
            )
        ).scalar_one_or_none() is not None
    return ReplyResponse(
        id=reply.id,
        post_id=reply.post_id,
        author=await author_summary(session, reply.author_user_id),
        body=reply.body,
        parent_reply_id=reply.parent_reply_id,
        like_count=like_count,
        liked=liked,
        children=children or [],
        created_at=reply.created_at,
    )


async def build_reply_tree(
    session: AsyncSession,
    replies: list[CommunityReply],
    user_id: str | None,
) -> list[ReplyResponse]:
    children_by_parent: dict[str, list[CommunityReply]] = {}
    roots: list[CommunityReply] = []
    for reply in replies:
        if reply.parent_reply_id:
            children_by_parent.setdefault(reply.parent_reply_id, []).append(reply)
        else:
            roots.append(reply)
    result: list[ReplyResponse] = []
    for root in roots:
        children = [
            await to_reply_response(session, child, user_id=user_id) for child in children_by_parent.get(root.id, [])
        ]
        result.append(await to_reply_response(session, root, user_id=user_id, children=children))
    return result


@router.get("", response_model=OfficialCommunityResponse)
async def get_community(
    identity: AuthenticatedIdentity | None = Depends(get_optional_identity),
    session: AsyncSession = Depends(get_database_session),
) -> OfficialCommunityResponse:
    community = await get_official_community(session)
    joined = False
    if identity is not None:
        joined = (
            await session.execute(
                select(CommunityMember.id).where(
                    CommunityMember.community_id == community.id,
                    CommunityMember.user_id == identity.user_id,
                )
            )
        ).scalar_one_or_none() is not None
    member_count = (
        await session.execute(
            select(func.count(col(CommunityMember.id))).where(CommunityMember.community_id == community.id)
        )
    ).scalar_one()
    post_count = (
        await session.execute(
            select(func.count(col(CommunityPost.id))).where(
                CommunityPost.community_id == community.id,
                CommunityPost.status == "published",
            )
        )
    ).scalar_one()
    return OfficialCommunityResponse(
        id=community.id,
        slug=community.slug,
        name=community.name,
        description=community.description,
        logo_url=community.logo_url,
        joined=joined,
        member_count=member_count,
        post_count=post_count,
    )


@router.patch("", response_model=OfficialCommunityResponse)
async def update_community(
    payload: OfficialCommunityUpdate,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> OfficialCommunityResponse:
    await require_creator(session, identity.user_id)
    community = await get_official_community(session)
    community.name = payload.name
    community.description = payload.description
    community.logo_url = payload.logo_url
    community.updated_at = utc_now()
    await session.commit()
    return await get_community(identity, session)


@router.post("/join", response_model=OfficialCommunityResponse)
async def join_community(
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> OfficialCommunityResponse:
    community = await get_official_community(session)
    membership = (
        await session.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == community.id,
                CommunityMember.user_id == identity.user_id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        try:
            membership = CommunityMember(community_id=community.id, user_id=identity.user_id)
            session.add(membership)
            await session.flush()
            await fan_token_service.award_rule(
                session,
                user_id=identity.user_id,
                rule_code="join-community",
                source_id=community.id,
                idempotency_key=f"join-community:{community.id}:{identity.user_id}",
                fallback_delta=50,
                fallback_description="加入 Fanora 官方社区",
            )
            await session.commit()
        except IntegrityError:
            await session.rollback()
    return await get_community(identity, session)


@router.get("/posts", response_model=list[PostSummaryResponse])
async def list_posts(
    category: str | None = Query(default=None, max_length=30),
    limit: int = Query(default=20, ge=1, le=50),
    identity: AuthenticatedIdentity | None = Depends(get_optional_identity),
    session: AsyncSession = Depends(get_database_session),
) -> list[PostSummaryResponse]:
    community = await get_official_community(session)
    query = select(CommunityPost).where(
        CommunityPost.community_id == community.id,
        CommunityPost.status == "published",
    )
    if category:
        query = query.where(CommunityPost.category == category)
    posts = list(
        (await session.execute(query.order_by(col(CommunityPost.updated_at).desc()).limit(limit))).scalars().all()
    )
    responses: list[PostSummaryResponse] = []
    for post in posts:
        like_count, bookmark_count, liked, bookmarked = await post_engagement(
            session, post.id, identity.user_id if identity else None
        )
        responses.append(
            PostSummaryResponse(
                id=post.id,
                title=post.title,
                body_preview=markdown_preview(post.body),
                cover_url=post.cover_url,
                category=post.category,
                reply_count=post.reply_count,
                like_count=like_count,
                bookmark_count=bookmark_count,
                liked=liked,
                bookmarked=bookmarked,
                author=await author_summary(session, post.author_user_id),
                created_at=post.created_at,
                updated_at=post.updated_at,
            )
        )
    return responses


@router.post("/posts", response_model=PostDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: PostCreate,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> PostDetailResponse:
    community = await get_official_community(session)
    membership = (
        await session.execute(
            select(CommunityMember.id).where(
                CommunityMember.community_id == community.id,
                CommunityMember.user_id == identity.user_id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Join the official community first")
    post = CommunityPost(
        community_id=community.id,
        author_user_id=identity.user_id,
        **payload.model_dump(),
    )
    session.add(post)
    await session.flush()
    await complete_claimed_tasks(
        session,
        user_id=identity.user_id,
        event=TaskCompletionEvent(
            task_type="content_publish",
            source_id=post.id,
            content_category=post.category,
            detail="The member published an eligible community creation.",
        ),
    )
    await session.commit()
    await session.refresh(post)
    return PostDetailResponse(
        id=post.id,
        title=post.title,
        body=post.body,
        cover_url=post.cover_url,
        category=post.category,
        reply_count=0,
        like_count=0,
        bookmark_count=0,
        liked=False,
        bookmarked=False,
        author=await author_summary(session, post.author_user_id),
        replies=[],
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


@router.get("/posts/{post_id}", response_model=PostDetailResponse)
async def get_post(
    post_id: str,
    identity: AuthenticatedIdentity | None = Depends(get_optional_identity),
    session: AsyncSession = Depends(get_database_session),
) -> PostDetailResponse:
    post = await session.get(CommunityPost, post_id)
    if post is None or post.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    replies = list(
        (
            await session.execute(
                select(CommunityReply)
                .where(CommunityReply.post_id == post.id, CommunityReply.status == "published")
                .order_by(col(CommunityReply.created_at))
            )
        )
        .scalars()
        .all()
    )
    like_count, bookmark_count, liked, bookmarked = await post_engagement(
        session, post.id, identity.user_id if identity else None
    )
    return PostDetailResponse(
        id=post.id,
        title=post.title,
        body=post.body,
        cover_url=post.cover_url,
        category=post.category,
        reply_count=post.reply_count,
        like_count=like_count,
        bookmark_count=bookmark_count,
        liked=liked,
        bookmarked=bookmarked,
        author=await author_summary(session, post.author_user_id),
        replies=await build_reply_tree(session, replies, identity.user_id if identity else None),
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


@router.post("/posts/{post_id}/replies", response_model=ReplyResponse, status_code=status.HTTP_201_CREATED)
async def create_reply(
    post_id: str,
    payload: ReplyCreate,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> ReplyResponse:
    post = await session.get(CommunityPost, post_id)
    if post is None or post.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    membership = (
        await session.execute(
            select(CommunityMember.id).where(
                CommunityMember.community_id == post.community_id,
                CommunityMember.user_id == identity.user_id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Join the official community first")

    parent_reply_id = payload.parent_reply_id
    if parent_reply_id:
        parent = await session.get(CommunityReply, parent_reply_id)
        if parent is None or parent.post_id != post.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent reply not found")
        if parent.parent_reply_id is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Comments support two levels only")
    reply = CommunityReply(
        post_id=post.id,
        author_user_id=identity.user_id,
        parent_reply_id=parent_reply_id,
        body=payload.body,
    )
    session.add(reply)
    await session.flush()
    post.reply_count += 1
    post.updated_at = utc_now()
    await fan_token_service.award_rule(
        session,
        user_id=identity.user_id,
        rule_code="valid-interaction",
        source_id=reply.id,
        idempotency_key=f"valid-interaction:reply:{reply.id}",
        fallback_delta=10,
        fallback_description="有效内容互动",
    )

    await complete_claimed_tasks(
        session,
        user_id=identity.user_id,
        event=TaskCompletionEvent(
            task_type="post_reply",
            source_id=reply.id,
            target_post_id=post.id,
            reply_id=reply.id,
            reply_length=len(payload.body),
            detail="The reply met the deterministic task rule; no manual review was required.",
        ),
    )
    await session.commit()
    await session.refresh(reply)
    return await to_reply_response(session, reply, user_id=identity.user_id)


async def require_post_interaction_access(
    session: AsyncSession, identity: AuthenticatedIdentity, post_id: str
) -> CommunityPost:
    post = await session.get(CommunityPost, post_id)
    if post is None or post.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    membership = (
        await session.execute(
            select(CommunityMember.id).where(
                CommunityMember.community_id == post.community_id,
                CommunityMember.user_id == identity.user_id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Join the official community first")
    return post


async def toggle_post_reaction(
    session: AsyncSession,
    *,
    post: CommunityPost,
    user_id: str,
    field: str,
) -> PostEngagementResponse:
    reaction = (
        await session.execute(
            select(CommunityPostReaction).where(
                CommunityPostReaction.post_id == post.id,
                CommunityPostReaction.user_id == user_id,
            )
        )
    ).scalar_one_or_none()
    if reaction is None:
        reaction = CommunityPostReaction(post_id=post.id, user_id=user_id)
        session.add(reaction)
    setattr(reaction, field, not bool(getattr(reaction, field)))
    reaction.updated_at = utc_now()
    await session.commit()
    like_count, bookmark_count, liked, bookmarked = await post_engagement(session, post.id, user_id)
    return PostEngagementResponse(
        post_id=post.id,
        liked=liked,
        bookmarked=bookmarked,
        like_count=like_count,
        bookmark_count=bookmark_count,
    )


@router.post("/posts/{post_id}/like", response_model=PostEngagementResponse)
async def toggle_post_like(
    post_id: str,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> PostEngagementResponse:
    post = await require_post_interaction_access(session, identity, post_id)
    return await toggle_post_reaction(session, post=post, user_id=identity.user_id, field="liked")


@router.post("/posts/{post_id}/bookmark", response_model=PostEngagementResponse)
async def toggle_post_bookmark(
    post_id: str,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> PostEngagementResponse:
    post = await require_post_interaction_access(session, identity, post_id)
    return await toggle_post_reaction(session, post=post, user_id=identity.user_id, field="bookmarked")


@router.post("/replies/{reply_id}/like", response_model=ReplyEngagementResponse)
async def toggle_reply_like(
    reply_id: str,
    identity: AuthenticatedIdentity = Depends(require_official_member),
    session: AsyncSession = Depends(get_database_session),
) -> ReplyEngagementResponse:
    reply = await session.get(CommunityReply, reply_id)
    if reply is None or reply.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reply not found")
    await require_post_interaction_access(session, identity, reply.post_id)
    like = (
        await session.execute(
            select(CommunityReplyLike).where(
                CommunityReplyLike.reply_id == reply.id,
                CommunityReplyLike.user_id == identity.user_id,
            )
        )
    ).scalar_one_or_none()
    liked = like is None
    if like is None:
        session.add(CommunityReplyLike(reply_id=reply.id, user_id=identity.user_id))
    else:
        await session.delete(like)
    await session.commit()
    like_count = (
        await session.execute(
            select(func.count(col(CommunityReplyLike.id))).where(CommunityReplyLike.reply_id == reply.id)
        )
    ).scalar_one()
    return ReplyEngagementResponse(reply_id=reply.id, liked=liked, like_count=like_count)
