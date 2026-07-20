"""Creator-owned community browsing and membership endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from app.core.database import get_database_session
from app.core.security import get_current_identity
from app.models.base import utc_now
from app.models.user import Community, CommunityMember, UserRole
from app.schemas.auth import CommunityCreate, CommunitySummary, CommunityUpdate
from app.services.identity import AuthenticatedIdentity

router = APIRouter(prefix="/communities")


async def require_creator(session: AsyncSession, user_id: str) -> None:
    role = (
        await session.execute(
            select(UserRole).where(UserRole.user_id == user_id, col(UserRole.role).in_(["creator", "admin"]))
        )
    ).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Creator role required")


def to_summary(community: Community, *, joined: bool = False) -> CommunitySummary:
    return CommunitySummary(
        id=community.id,
        slug=community.slug,
        name=community.name,
        description=community.description,
        logo_url=community.logo_url,
        owner_user_id=community.owner_user_id,
        is_public=community.is_public,
        joined=joined,
    )


@router.get("", response_model=list[CommunitySummary])
async def list_communities(
    search: str = Query(default="", max_length=80),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=50),
    session: AsyncSession = Depends(get_database_session),
) -> list[CommunitySummary]:
    query = select(Community).where(col(Community.is_public).is_(True))
    if search.strip():
        query = query.where(func.lower(col(Community.name)).contains(search.strip().lower()))
    communities = list(
        (await session.execute(query.order_by(col(Community.created_at).desc()).offset(offset).limit(limit))).scalars().all()
    )
    return [to_summary(community) for community in communities]


@router.post("", response_model=CommunitySummary, status_code=status.HTTP_201_CREATED)
async def create_community(
    payload: CommunityCreate,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> CommunitySummary:
    await require_creator(session, identity.user_id)
    community = Community(owner_user_id=identity.user_id, **payload.model_dump())
    session.add(community)
    await session.flush()
    session.add(CommunityMember(community_id=community.id, user_id=identity.user_id, role="owner"))
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Community slug is already in use") from error
    await session.refresh(community)
    return to_summary(community, joined=True)


@router.patch("/{community_id}", response_model=CommunitySummary)
async def update_community(
    community_id: str,
    payload: CommunityUpdate,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> CommunitySummary:
    community = await session.get(Community, community_id)
    if community is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")
    if community.owner_user_id != identity.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the community owner can edit it")
    for field, value in payload.model_dump().items():
        setattr(community, field, value)
    community.updated_at = utc_now()
    await session.commit()
    await session.refresh(community)
    return to_summary(community, joined=True)


@router.post("/{community_id}/join", response_model=CommunitySummary)
async def join_community(
    community_id: str,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> CommunitySummary:
    community = await session.get(Community, community_id)
    if community is None or not community.is_public:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")
    membership = (
        await session.execute(
            select(CommunityMember).where(
                CommunityMember.community_id == community_id,
                CommunityMember.user_id == identity.user_id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        session.add(CommunityMember(community_id=community_id, user_id=identity.user_id))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
    return to_summary(community, joined=True)
