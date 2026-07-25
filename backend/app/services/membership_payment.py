"""Monad payment verification for becoming an official Fanora member."""

import asyncio
from dataclasses import dataclass

from fastapi import HTTPException, status
from hexbytes import HexBytes
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from web3 import Web3
from web3.exceptions import TransactionNotFound

from app.adapters.monad import monad_contract_adapter
from app.core.config import settings
from app.models.base import utc_now
from app.models.user import OfficialMembershipPayment, UserProfile
from app.services.fan_tokens import fan_token_service
from app.services.identity import AuthenticatedIdentity


@dataclass(frozen=True, slots=True)
class ConfirmedChainPayment:
    transaction_hash: str
    from_address: str
    to_address: str
    treasury_address: str
    payment_id: str
    value_wei: int
    chain_id: int
    block_number: int
    confirmations: int


class OfficialMembershipPaymentService:
    def configured_gateway(self) -> str:
        if not settings.membership_payment_contract_address or not Web3.is_address(
            settings.membership_payment_contract_address
        ):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Official membership payment contract is not configured",
            )
        return Web3.to_checksum_address(settings.membership_payment_contract_address)

    @staticmethod
    def payment_id_for_user(user_id: str) -> str:
        return Web3.to_hex(Web3.keccak(text=f"fanora-membership:{user_id}"))

    async def _load_chain_payment(self, transaction_hash: str) -> ConfirmedChainPayment:
        def load() -> ConfirmedChainPayment:
            web3 = Web3(Web3.HTTPProvider(settings.monad_rpc_url, request_kwargs={"timeout": 50}))
            if not web3.is_connected():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Monad RPC is temporarily unavailable",
                )
            try:
                transaction_hash_bytes = HexBytes(transaction_hash)
                receipt = web3.eth.get_transaction_receipt(transaction_hash_bytes)
                transaction = web3.eth.get_transaction(transaction_hash_bytes)
            except TransactionNotFound as error:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Membership payment is still waiting for confirmation",
                ) from error

            if int(receipt["status"]) != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Membership payment transaction failed onchain",
                )
            block_number = int(receipt["blockNumber"])
            confirmations = max(int(web3.eth.block_number) - block_number + 1, 0)
            from_address = transaction.get("from")
            to_address = transaction.get("to")
            value_wei = transaction.get("value")
            if from_address is None or to_address is None or value_wei is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Membership payment transaction is missing transfer fields",
                )
            gateway = web3.eth.contract(
                address=Web3.to_checksum_address(self.configured_gateway()),
                abi=monad_contract_adapter.membership_gateway_abi,
            )
            events = gateway.events.MembershipPaid().process_receipt(receipt)
            if len(events) != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Transaction does not contain one valid MembershipPaid event",
                )
            event = events[0]["args"]
            if Web3.to_checksum_address(event["account"]) != Web3.to_checksum_address(from_address):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="MembershipPaid account does not match the transaction sender",
                )
            if int(event["amount"]) != int(value_wei):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="MembershipPaid amount does not match the transaction value",
                )
            return ConfirmedChainPayment(
                transaction_hash=transaction_hash.lower(),
                from_address=Web3.to_checksum_address(from_address),
                to_address=Web3.to_checksum_address(to_address),
                treasury_address=Web3.to_checksum_address(event["treasury"]),
                payment_id=Web3.to_hex(event["paymentId"]),
                value_wei=int(value_wei),
                chain_id=int(web3.eth.chain_id),
                block_number=block_number,
                confirmations=confirmations,
            )

        return await asyncio.to_thread(load)

    async def verify_and_activate(
        self,
        session: AsyncSession,
        identity: AuthenticatedIdentity,
        transaction_hash: str,
    ) -> OfficialMembershipPayment:
        gateway_address = self.configured_gateway()
        profile = await session.get(UserProfile, identity.user_id)
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found")

        existing_payment = (
            await session.execute(
                select(OfficialMembershipPayment).where(OfficialMembershipPayment.user_id == identity.user_id)
            )
        ).scalar_one_or_none()
        if profile.is_official_member and existing_payment is not None:
            if existing_payment.transaction_hash != transaction_hash.lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Official membership is already linked to another transaction",
                )
            return existing_payment

        reused_payment = (
            await session.execute(
                select(OfficialMembershipPayment).where(
                    OfficialMembershipPayment.transaction_hash == transaction_hash.lower()
                )
            )
        ).scalar_one_or_none()
        if reused_payment is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This transaction was already used for another membership",
            )

        payment = await self._load_chain_payment(transaction_hash)
        if payment.chain_id != settings.monad_chain_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment was sent on the wrong chain")
        if payment.from_address != Web3.to_checksum_address(identity.primary_wallet):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment sender does not match the signed-in primary wallet",
            )
        if payment.to_address != gateway_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Payment was not sent through the membership contract"
            )
        if payment.payment_id != self.payment_id_for_user(identity.user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Membership payment id does not match this user"
            )
        if payment.confirmations < settings.membership_min_confirmations:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Membership payment does not have enough confirmations yet",
            )

        now = utc_now()
        record = OfficialMembershipPayment(
            user_id=identity.user_id,
            wallet_address=payment.from_address,
            treasury_address=payment.treasury_address,
            transaction_hash=payment.transaction_hash,
            chain_id=payment.chain_id,
            amount_wei=payment.value_wei,
            block_number=payment.block_number,
            confirmed_at=now,
        )
        session.add(record)
        await fan_token_service.sync_level(session, profile)
        profile.is_official_member = True
        profile.official_member_since = now
        profile.updated_at = now
        try:
            await session.commit()
        except IntegrityError as error:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Membership payment was activated by another request",
            ) from error
        await session.refresh(record)
        return record

    async def activate_free_membership(
        self,
        session: AsyncSession,
        identity: AuthenticatedIdentity,
    ) -> OfficialMembershipPayment:
        profile = await session.get(UserProfile, identity.user_id)
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found")

        existing_payment = (
            await session.execute(
                select(OfficialMembershipPayment).where(OfficialMembershipPayment.user_id == identity.user_id)
            )
        ).scalar_one_or_none()
        if profile.is_official_member and existing_payment is not None:
            return existing_payment

        if not monad_contract_adapter.membership_gateway_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Free membership relayer is not configured",
            )
        try:
            receipt = await monad_contract_adapter.activate_free_membership(
                identity.primary_wallet,
                self.payment_id_for_user(identity.user_id),
            )
        except Exception as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Free membership activation failed onchain",
            ) from error

        now = utc_now()
        treasury_address = receipt.event_args.get("treasury")
        record = OfficialMembershipPayment(
            user_id=identity.user_id,
            wallet_address=Web3.to_checksum_address(identity.primary_wallet),
            treasury_address=Web3.to_checksum_address(
                treasury_address or settings.membership_treasury_address or identity.primary_wallet
            ),
            transaction_hash=receipt.transaction_hash.lower(),
            chain_id=settings.monad_chain_id,
            amount_wei=0,
            block_number=receipt.block_number,
            confirmed_at=now,
        )
        session.add(record)
        await fan_token_service.sync_level(session, profile)
        profile.is_official_member = True
        profile.official_member_since = now
        profile.updated_at = now
        try:
            await session.commit()
        except IntegrityError as error:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Membership was activated by another request",
            ) from error
        await session.refresh(record)
        return record


official_membership_payment_service = OfficialMembershipPaymentService()
