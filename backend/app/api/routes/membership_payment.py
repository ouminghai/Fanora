"""Official Fanora membership payment and status endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import settings
from app.core.database import get_database_session
from app.core.security import get_current_identity
from app.models.user import OfficialMembershipPayment, UserProfile
from app.schemas.membership import OfficialMembershipStatusResponse, OfficialMembershipVerifyRequest
from app.services.identity import AuthenticatedIdentity
from app.services.membership_payment import official_membership_payment_service

router = APIRouter(prefix="/membership")


def status_response(
    profile: UserProfile,
    payment: OfficialMembershipPayment | None,
) -> OfficialMembershipStatusResponse:
    treasury_address: str | None = None
    try:
        treasury_address = official_membership_payment_service.configured_treasury()
    except HTTPException:
        treasury_address = None
    return OfficialMembershipStatusResponse(
        status="active" if profile.is_official_member else "pending_payment",
        is_official_member=profile.is_official_member,
        fee_mon="1",
        fee_wei=str(settings.membership_fee_wei),
        treasury_address=treasury_address,
        chain_id=settings.monad_chain_id,
        transaction_hash=payment.transaction_hash if payment else None,
        joined_at=profile.official_member_since,
    )


@router.get("/me", response_model=OfficialMembershipStatusResponse)
async def get_membership_status(
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> OfficialMembershipStatusResponse:
    profile = await session.get(UserProfile, identity.user_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found")
    payment = (
        await session.execute(
            select(OfficialMembershipPayment).where(OfficialMembershipPayment.user_id == identity.user_id)
        )
    ).scalar_one_or_none()
    return status_response(profile, payment)


@router.post("/verify", response_model=OfficialMembershipStatusResponse)
async def verify_membership_payment(
    payload: OfficialMembershipVerifyRequest,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> OfficialMembershipStatusResponse:
    payment = await official_membership_payment_service.verify_and_activate(
        session,
        identity,
        payload.transaction_hash,
    )
    profile = await session.get(UserProfile, identity.user_id)
    assert profile is not None
    return status_response(profile, payment)
