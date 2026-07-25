"""Single official-community content and membership endpoints."""

import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from app.api.routes.nft import _fan_nft_listing_response
from app.core.database import get_database_session
from app.core.security import get_current_identity, get_optional_identity, require_official_member
from app.models.base import utc_now
from app.models.community import (
    CommunityPost,
    CommunityPostReaction,
    CommunityReply,
    CommunityReplyLike,
    FanTokenLedger,
)
from app.models.nft import NftApplication
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
from app.services.community_moderation import moderate_community_content
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


async def linked_nft_response(session: AsyncSession, post: CommunityPost, user_id: str | None):
    if not post.linked_nft_creation_id:
        return None
    application = await session.get(NftApplication, post.linked_nft_creation_id)
    if application is None or application.status not in {"MINTED", "MINTING", "FAILED"}:
        return None
    return await _fan_nft_listing_response(session, application, user_id=user_id)


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
        image_urls=reply.image_urls,
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
                fallback_description="加入 Fanora 链上社区",
            )
            await session.commit()
        except IntegrityError:
            await session.rollback()
    return await get_community(identity, session)


@router.get("/posts", response_model=list[PostSummaryResponse])
async def list_posts(
    category: str | None = Query(default=None, max_length=30),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=10_000),
    sort: str = Query(default="latest", pattern="^(latest|hot)$"),
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
    if sort == "latest":
        posts = list(
            (
                await session.execute(
                    query.order_by(col(CommunityPost.updated_at).desc(), col(CommunityPost.id).desc())
                    .offset(offset)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
    else:
        posts = list((await session.execute(query)).scalars().all())
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
                image_urls=post.image_urls,
                category=post.category,
                reply_count=post.reply_count,
                like_count=like_count,
                bookmark_count=bookmark_count,
                liked=liked,
                bookmarked=bookmarked,
                author=await author_summary(session, post.author_user_id),
                linked_nft=await linked_nft_response(session, post, identity.user_id if identity else None),
                created_at=post.created_at,
                updated_at=post.updated_at,
            )
        )
    if sort == "hot":
        responses.sort(
            key=lambda post: (post.reply_count * 3 + post.like_count * 2 + post.bookmark_count * 2, post.updated_at),
            reverse=True,
        )
        return responses[offset : offset + limit]
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
    moderation = await moderate_community_content(
        content_type="post",
        source_id="pre-publish",
        title=payload.title,
        body=payload.body,
        category=payload.category,
    )
    if moderation.decision == "rejected":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="内容与社区主题不够相关，或像无意义/垃圾信息。")
    if payload.linked_nft_creation_id:
        linked_nft = await session.get(NftApplication, payload.linked_nft_creation_id)
        if (
            linked_nft is None
            or linked_nft.user_id != identity.user_id
            or linked_nft.status not in {"MINTED", "MINTING", "FAILED"}
            or not linked_nft.collectible_token_type_id
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Linked NFT must be one of your published NFT items",
            )
    post = CommunityPost(
        community_id=community.id,
        author_user_id=identity.user_id,
        **payload.model_dump(),
    )
    session.add(post)
    await session.flush()
    await fan_token_service.award_rule(
        session,
        user_id=identity.user_id,
        rule_code="post-publish",
        source_id=post.id,
        idempotency_key=f"post-publish:{post.id}",
        fallback_delta=5,
        fallback_description="发布帖子",
    )
    await complete_claimed_tasks(
        session,
        user_id=identity.user_id,
        event=TaskCompletionEvent(
            task_type="content_publish",
            source_id=post.id,
            content_category=post.category,
            content_title=post.title,
            content_text=post.body,
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
        image_urls=post.image_urls,
        category=post.category,
        reply_count=0,
        like_count=0,
        bookmark_count=0,
        liked=False,
        bookmarked=False,
        author=await author_summary(session, post.author_user_id),
        linked_nft=await linked_nft_response(session, post, identity.user_id),
        replies=[],
        has_more_replies=False,
        next_replies_offset=None,
        created_at=post.created_at,
        updated_at=post.updated_at,
    )


@router.get("/posts/{post_id}", response_model=PostDetailResponse)
async def get_post(
    post_id: str,
    reply_limit: int = Query(default=10, ge=1, le=50),
    reply_offset: int = Query(default=0, ge=0),
    identity: AuthenticatedIdentity | None = Depends(get_optional_identity),
    session: AsyncSession = Depends(get_database_session),
) -> PostDetailResponse:
    post = await session.get(CommunityPost, post_id)
    if post is None or post.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    roots = list(
        (
            await session.execute(
                select(CommunityReply)
                .where(
                    CommunityReply.post_id == post.id,
                    CommunityReply.status == "published",
                    col(CommunityReply.parent_reply_id).is_(None),
                )
                .order_by(col(CommunityReply.created_at))
                .offset(reply_offset)
                .limit(reply_limit + 1)
            )
        )
        .scalars()
        .all()
    )
    has_more_replies = len(roots) > reply_limit
    roots = roots[:reply_limit]
    root_ids = [reply.id for reply in roots]
    children = []
    if root_ids:
        children = list(
            (
                await session.execute(
                    select(CommunityReply)
                    .where(
                        CommunityReply.post_id == post.id,
                        CommunityReply.status == "published",
                        col(CommunityReply.parent_reply_id).in_(root_ids),
                    )
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
        image_urls=post.image_urls,
        category=post.category,
        reply_count=post.reply_count,
        like_count=like_count,
        bookmark_count=bookmark_count,
        liked=liked,
        bookmarked=bookmarked,
        author=await author_summary(session, post.author_user_id),
        linked_nft=await linked_nft_response(session, post, identity.user_id if identity else None),
        replies=await build_reply_tree(session, [*roots, *children], identity.user_id if identity else None),
        has_more_replies=has_more_replies,
        next_replies_offset=reply_offset + reply_limit if has_more_replies else None,
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
    moderation = await moderate_community_content(
        content_type="reply",
        source_id=f"post:{post.id}",
        body=payload.body,
        category=post.category,
    )
    if moderation.decision == "rejected":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="回复与社区主题不够相关，或像无意义/垃圾信息。")

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
        image_urls=payload.image_urls,
    )
    session.add(reply)
    await session.flush()
    post.reply_count += 1
    post.updated_at = utc_now()
    await fan_token_service.award_rule(
        session,
        user_id=identity.user_id,
        rule_code="post-reply",
        source_id=reply.id,
        idempotency_key=f"post-reply:{reply.id}",
        fallback_delta=1,
        fallback_description="回复帖子",
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
            content_text=payload.body,
            detail="The reply was submitted to the Quest content-review workflow.",
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
    next_value = not bool(getattr(reaction, field))
    setattr(reaction, field, next_value)
    reaction.updated_at = utc_now()
    if field == "liked" and next_value:
        await fan_token_service.award_rule(
            session,
            user_id=user_id,
            rule_code="post-like",
            source_id=post.id,
            idempotency_key=f"post-like:{post.id}:{user_id}",
            fallback_delta=1,
            fallback_description="点赞帖子",
        )
    if field == "bookmarked" and next_value and post.author_user_id != user_id:
        await session.execute(select(CommunityPost.id).where(CommunityPost.id == post.id).with_for_update())
        author_profile = await session.get(UserProfile, post.author_user_id)
        rewarded_bookmarks = (
            await session.execute(
                select(func.count(col(FanTokenLedger.id))).where(
                    FanTokenLedger.source_type == "rule:post-bookmark-received",
                    FanTokenLedger.source_id == post.id,
                )
            )
        ).scalar_one()
        if author_profile is not None and rewarded_bookmarks < 10:
            await fan_token_service.award_rule(
                session,
                user_id=post.author_user_id,
                rule_code="post-bookmark-received",
                source_id=post.id,
                idempotency_key=f"post-bookmark-received:{post.id}:{user_id}",
                fallback_delta=1,
                fallback_description="帖子被收藏",
            )
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
