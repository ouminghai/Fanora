"""Read-only Fan Token history plus audited administrator adjustments."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app.core.database import get_database_session
from app.core.security import get_current_identity
from app.models.community import FanTokenLedger
from app.models.user import User, UserRole
from app.schemas.community import FanTokenAdjustmentCreate, FanTokenLedgerResponse
from app.services.fan_tokens import fan_token_service
from app.services.identity import AuthenticatedIdentity

router = APIRouter(prefix="/fan-tokens")


@router.get("/me/ledger", response_model=list[FanTokenLedgerResponse])
async def get_my_ledger(
    limit: int = Query(default=50, ge=1, le=100),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> list[FanTokenLedger]:
    return list(
        (
            await session.execute(
                select(FanTokenLedger)
                .where(FanTokenLedger.user_id == identity.user_id)
                .order_by(col(FanTokenLedger.created_at).desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )


@router.post("/admin/adjustments", response_model=FanTokenLedgerResponse)
async def create_adjustment(
    payload: FanTokenAdjustmentCreate,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> FanTokenLedger:
    admin = (
        await session.execute(
            select(UserRole.id).where(UserRole.user_id == identity.user_id, UserRole.role == "admin")
        )
    ).scalar_one_or_none()
    if admin is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    if await session.get(User, payload.user_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    entry = await fan_token_service.award(
        session,
        user_id=payload.user_id,
        delta=payload.delta,
        source_type="admin-adjustment",
        source_id=identity.user_id,
        idempotency_key=f"admin-adjustment:{payload.operation_id}",
        description=payload.reason,
    )
    await session.commit()
    return entry
