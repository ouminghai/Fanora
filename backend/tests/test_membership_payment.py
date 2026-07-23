from datetime import timedelta
from types import SimpleNamespace

import pytest
from eth_account import Account
from fastapi import HTTPException

from app.adapters.monad import monad_contract_adapter
from app.core.config import settings
from app.core.database import database_service
from app.models.base import utc_now
from app.models.membership import MembershipLevel
from app.models.user import OfficialMembershipPayment, User, UserProfile, UserSession, Wallet
from app.services.auth import hash_session_token
from app.services.identity import AuthenticatedIdentity
from app.services.membership_payment import ConfirmedChainPayment, official_membership_payment_service
from app.services.nft import nft_service


def test_membership_payment_id_is_a_prefixed_bytes32():
    payment_id = official_membership_payment_service.payment_id_for_user("user-1")

    assert payment_id.startswith("0x")
    assert len(payment_id) == 66
    assert bytes.fromhex(payment_id[2:])


async def test_active_membership_verification_is_idempotent_only_for_its_original_transaction(monkeypatch):
    transaction_hash = "0x" + "ab" * 32
    gateway = Account.create().address
    wallet = Account.create().address
    profile = UserProfile(user_id="user-1", is_official_member=True)
    payment = OfficialMembershipPayment(
        user_id=profile.user_id,
        wallet_address=wallet,
        treasury_address=Account.create().address,
        transaction_hash=transaction_hash,
        chain_id=10143,
        amount_wei=10**18,
        block_number=123,
    )

    class FakeResult:
        def scalar_one_or_none(self):
            return payment

    class FakeSession:
        async def get(self, model, object_id):
            assert model is UserProfile
            assert object_id == profile.user_id
            return profile

        async def execute(self, _statement):
            return FakeResult()

    monkeypatch.setattr(settings, "membership_payment_contract_address", gateway)
    identity = AuthenticatedIdentity(
        user_id=profile.user_id,
        primary_wallet=wallet,
        wallet_type="external",
        provider="rainbowkit",
    )

    repeated = await official_membership_payment_service.verify_and_activate(
        FakeSession(),  # type: ignore[arg-type]
        identity,
        transaction_hash,
    )
    assert repeated is payment

    with pytest.raises(HTTPException, match="already linked to another transaction") as error:
        await official_membership_payment_service.verify_and_activate(
            FakeSession(),  # type: ignore[arg-type]
            identity,
            "0x" + "cd" * 32,
        )
    assert error.value.status_code == 409


async def test_verified_one_mon_payment_activates_official_membership(client, monkeypatch):
    account = Account.create()
    treasury = Account.create().address
    raw_token = "membership-test-session-token"
    transaction_hash = "0x" + "ab" * 32

    async with database_service.session() as session:
        session.add(
            MembershipLevel(
                code="mild-neuro",
                name="轻度神经",
                description="初级活跃会员",
                rank=2,
                min_token_balance=100,
                max_token_balance=499,
                badge_image_url="/img/badges/mild.png",
            )
        )
        user = User(display_name="Pending Member")
        session.add(user)
        await session.flush()
        session.add_all(
            [
                UserProfile(user_id=user.id, fan_token_balance=100, level="新生儿"),
                Wallet(
                    user_id=user.id,
                    address=account.address,
                    wallet_type="embedded",
                    provider="wallet",
                    is_primary=True,
                ),
                UserSession(
                    user_id=user.id,
                    token_hash=hash_session_token(raw_token),
                    expires_at=utc_now() + timedelta(hours=1),
                ),
            ]
        )
        await session.commit()
        user_id = user.id

    gateway = Account.create().address
    monkeypatch.setattr(settings, "membership_payment_contract_address", gateway)
    monkeypatch.setattr(settings, "membership_identity_contract_address", Account.create().address)
    monkeypatch.setattr(settings, "identity_minter_private_key", "0x" + "11" * 32)
    monkeypatch.setattr(settings, "pinata_jwt", "test-pinata-jwt")

    async def current_fee() -> int:
        return settings.membership_fee_wei

    monkeypatch.setattr(monad_contract_adapter, "membership_fee", current_fee)

    async def confirmed_payment(_: str) -> ConfirmedChainPayment:
        return ConfirmedChainPayment(
            transaction_hash=transaction_hash,
            from_address=account.address,
            to_address=gateway,
            treasury_address=treasury,
            payment_id=official_membership_payment_service.payment_id_for_user(user_id),
            value_wei=settings.membership_fee_wei,
            chain_id=settings.monad_chain_id,
            block_number=123,
            confirmations=1,
        )

    monkeypatch.setattr(official_membership_payment_service, "_load_chain_payment", confirmed_payment)
    identity_syncs: list[str] = []

    async def sync_identity(_session, identity):
        identity_syncs.append(identity.user_id)
        return SimpleNamespace(status="CONFIRMED")

    monkeypatch.setattr(nft_service, "ensure_membership_identity", sync_identity)
    headers = {"Authorization": f"Bearer {raw_token}"}

    pending_response = client.get("/api/v1/membership/me", headers=headers)
    assert pending_response.status_code == 200
    assert pending_response.json()["status"] == "pending_payment"
    assert pending_response.json()["is_official_member"] is False
    assert pending_response.json()["fee_mon"] == "1"

    verify_response = client.post(
        "/api/v1/membership/verify",
        headers=headers,
        json={"transaction_hash": transaction_hash},
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["status"] == "active"
    assert verify_response.json()["transaction_hash"] == transaction_hash
    assert verify_response.json()["identity_nft_status"] == "CONFIRMED"
    assert identity_syncs == [user_id]

    repeated_response = client.post(
        "/api/v1/membership/verify",
        headers=headers,
        json={"transaction_hash": transaction_hash},
    )
    assert repeated_response.status_code == 200

    different_transaction_response = client.post(
        "/api/v1/membership/verify",
        headers=headers,
        json={"transaction_hash": "0x" + "cd" * 32},
    )
    assert different_transaction_response.status_code == 409
    assert different_transaction_response.json()["detail"] == (
        "Official membership is already linked to another transaction"
    )

    me_response = client.get("/api/v1/users/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["is_official_member"] is True
    assert me_response.json()["level"] == "轻度神经"


async def test_membership_status_does_not_offer_payment_without_gateway(client):
    account = Account.create()
    raw_token = "membership-unconfigured-session-token"

    async with database_service.session() as session:
        user = User(display_name="Unconfigured Member")
        session.add(user)
        await session.flush()
        session.add_all(
            [
                UserProfile(user_id=user.id),
                Wallet(user_id=user.id, address=account.address, wallet_type="external", is_primary=True),
                UserSession(
                    user_id=user.id,
                    token_hash=hash_session_token(raw_token),
                    expires_at=utc_now() + timedelta(hours=1),
                ),
            ]
        )
        await session.commit()

    response = client.get(
        "/api/v1/membership/me",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert response.status_code == 200
    assert response.json()["payment_contract_address"] is None
