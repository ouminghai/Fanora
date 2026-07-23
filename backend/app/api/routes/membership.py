"""Public membership level and Badge presentation endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.core.database import get_database_session
from app.models.membership import MembershipLevel
from app.schemas.membership import MembershipLevelResponse

router = APIRouter(prefix="/membership-levels")


@router.get("", response_model=list[MembershipLevelResponse])
async def list_membership_levels(
    session: AsyncSession = Depends(get_database_session),
) -> list[MembershipLevel]:
    return list(
        (
            await session.execute(
                select(MembershipLevel)
                .where(col(MembershipLevel.is_active).is_(True))
                .order_by(col(MembershipLevel.rank))
            )
        )
        .scalars()
        .all()
    )
