"""Official Fanora membership payment and status endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from web3 import Web3

from app.adapters.monad import ChainConfigurationError, monad_contract_adapter
from app.adapters.pinata import pinata_adapter
from app.core.config import settings
from app.core.database import get_database_session
from app.core.logging import logger
from app.core.security import get_current_identity
from app.models.nft import MembershipIdentityNft
from app.models.user import OfficialMembershipPayment, UserProfile, UserRole
from app.schemas.membership import (
    MembershipFeeResponse,
    MembershipFeeUpdateRequest,
    MembershipTreasuryResponse,
    MembershipTreasuryWithdrawRequest,
    OfficialMembershipStatusResponse,
    OfficialMembershipVerifyRequest,
)
from app.services.identity import AuthenticatedIdentity
from app.services.membership_fee import membership_fee_service
from app.services.membership_payment import official_membership_payment_service

router = APIRouter(prefix="/membership")


async def require_admin(session: AsyncSession, user_id: str) -> None:
    admin = (
        await session.execute(select(UserRole.id).where(UserRole.user_id == user_id, UserRole.role == "admin"))
    ).scalar_one_or_none()
    if admin is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")


async def current_membership_fee() -> int:
    return await membership_fee_service.get_status_fee()


async def status_response(
    profile: UserProfile,
    payment: OfficialMembershipPayment | None,
    identity_nft_status: str = "NOT_CONFIGURED",
) -> OfficialMembershipStatusResponse:
    payment_contract_address: str | None = None
    try:
        payment_contract_address = official_membership_payment_service.configured_gateway()
    except HTTPException:
        payment_contract_address = None
    fee_wei = await current_membership_fee()
    return OfficialMembershipStatusResponse(
        status="active" if profile.is_official_member else "pending_payment",
        is_official_member=profile.is_official_member,
        fee_mon=str(Web3.from_wei(fee_wei, "ether")),
        fee_wei=str(fee_wei),
        treasury_address=payment.treasury_address if payment else None,
        payment_contract_address=payment_contract_address,
        payment_id=(
            official_membership_payment_service.payment_id_for_user(profile.user_id)
            if payment_contract_address
            else None
        ),
        chain_id=settings.monad_chain_id,
        transaction_hash=payment.transaction_hash if payment else None,
        joined_at=profile.official_member_since,
        identity_nft_status=identity_nft_status,
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
    identity_nft_status = (
        await session.execute(
            select(MembershipIdentityNft.status).where(MembershipIdentityNft.user_id == identity.user_id)
        )
    ).scalar_one_or_none() or "NOT_CONFIGURED"
    return await status_response(profile, payment, identity_nft_status)


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
    identity_nft_status = (
        await session.execute(
            select(MembershipIdentityNft.status).where(MembershipIdentityNft.user_id == identity.user_id)
        )
    ).scalar_one_or_none() or (
        "READY" if pinata_adapter.configured and monad_contract_adapter.identity_configured else "NOT_CONFIGURED"
    )
    return await status_response(profile, payment, identity_nft_status)


@router.post("/activate-free", response_model=OfficialMembershipStatusResponse)
async def activate_free_membership(
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> OfficialMembershipStatusResponse:
    fee_wei = settings.membership_fee_wei
    if fee_wei != 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Official membership is not free right now")
    payment = await official_membership_payment_service.activate_free_membership(session, identity)
    profile = await session.get(UserProfile, identity.user_id)
    assert profile is not None
    identity_nft_status = (
        await session.execute(
            select(MembershipIdentityNft.status).where(MembershipIdentityNft.user_id == identity.user_id)
        )
    ).scalar_one_or_none() or (
        "READY" if pinata_adapter.configured and monad_contract_adapter.identity_configured else "NOT_CONFIGURED"
    )
    return await status_response(profile, payment, identity_nft_status)


@router.get("/admin/treasury", response_model=MembershipTreasuryResponse)
async def membership_treasury_status(
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> MembershipTreasuryResponse:
    await require_admin(session, identity.user_id)
    try:
        contract_address = official_membership_payment_service.configured_gateway()
        balance = await monad_contract_adapter.membership_gateway_balance()
    except (HTTPException, ChainConfigurationError) as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    return MembershipTreasuryResponse(
        contract_address=contract_address,
        treasury_address=settings.membership_treasury_address or None,
        balance_wei=str(balance),
        balance_mon=str(Web3.from_wei(balance, "ether")),
    )


@router.post("/admin/treasury/withdraw", response_model=MembershipTreasuryResponse)
async def withdraw_membership_treasury(
    payload: MembershipTreasuryWithdrawRequest,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> MembershipTreasuryResponse:
    await require_admin(session, identity.user_id)
    if not monad_contract_adapter.membership_gateway_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Treasury manager is not configured"
        )
    try:
        receipt = await monad_contract_adapter.withdraw_membership_fees(payload.amount_wei)
        balance = await monad_contract_adapter.membership_gateway_balance()
    except Exception as error:
        logger.exception("membership_treasury_withdraw_failed", user_id=identity.user_id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Membership withdrawal failed") from error
    return MembershipTreasuryResponse(
        contract_address=official_membership_payment_service.configured_gateway(),
        treasury_address=str(receipt.event_args.get("treasury") or settings.membership_treasury_address or "") or None,
        balance_wei=str(balance),
        balance_mon=str(Web3.from_wei(balance, "ether")),
        transaction_hash=receipt.transaction_hash,
        block_number=receipt.block_number,
    )


@router.put("/admin/fee", response_model=MembershipFeeResponse)
async def update_membership_fee(
    payload: MembershipFeeUpdateRequest,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_database_session),
) -> MembershipFeeResponse:
    await require_admin(session, identity.user_id)
    if not monad_contract_adapter.membership_gateway_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Treasury manager is not configured"
        )
    try:
        receipt = await monad_contract_adapter.set_membership_fee(payload.fee_wei)
        fee_wei = payload.fee_wei
        await membership_fee_service.set_fee(fee_wei)
    except Exception as error:
        logger.exception("membership_fee_update_failed", user_id=identity.user_id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Membership fee update failed") from error
    return MembershipFeeResponse(
        contract_address=official_membership_payment_service.configured_gateway(),
        fee_wei=str(fee_wei),
        fee_mon=str(Web3.from_wei(fee_wei, "ether")),
        transaction_hash=receipt.transaction_hash,
        block_number=receipt.block_number,
    )
