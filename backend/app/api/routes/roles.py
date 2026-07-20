"""Minimal administrator role management for creator access."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_database_session
from app.core.security import get_current_identity
from app.models.user import User, UserRole
from app.schemas.community import RoleGrantResponse
from app.services.identity import AuthenticatedIdentity

router = APIRouter(prefix="/admin/users")


@router.put("/{user_id}/roles/creator", response_model=RoleGrantResponse)
async def grant_creator_role(
    user_id: str,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> RoleGrantResponse:
    admin = (
        await session.execute(
            select(UserRole.id).where(UserRole.user_id == identity.user_id, UserRole.role == "admin")
        )
    ).scalar_one_or_none()
    if admin is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    if await session.get(User, user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    creator = (
        await session.execute(select(UserRole).where(UserRole.user_id == user_id, UserRole.role == "creator"))
    ).scalar_one_or_none()
    if creator is None:
        session.add(UserRole(user_id=user_id, role="creator"))
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
    roles = list((await session.execute(select(UserRole.role).where(UserRole.user_id == user_id))).scalars().all())
    return RoleGrantResponse(user_id=user_id, roles=sorted(roles))
