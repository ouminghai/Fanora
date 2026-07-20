"""Compatibility routes constrained to Fanora's single official community."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

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
    session: AsyncSession = Depends(get_database_session),
) -> list[CommunitySummary]:
    community = (
        await session.execute(
            select(Community).where(Community.slug == "fanora-official", col(Community.is_public).is_(True))
        )
    ).scalar_one_or_none()
    return [to_summary(community)] if community else []


@router.post("", response_model=CommunitySummary, status_code=status.HTTP_201_CREATED)
async def create_community(
    payload: CommunityCreate,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> CommunitySummary:
    del payload, identity, session
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Fanora MVP only supports the existing official community",
    )


@router.patch("/{community_id}", response_model=CommunitySummary)
async def update_community(
    community_id: str,
    payload: CommunityUpdate,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> CommunitySummary:
    community = await session.get(Community, community_id)
    if community is None or community.slug != "fanora-official":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Community not found")
    await require_creator(session, identity.user_id)
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
    if community is None or community.slug != "fanora-official" or not community.is_public:
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
