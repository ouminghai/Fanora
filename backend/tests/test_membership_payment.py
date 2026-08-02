from datetime import timedelta
from types import SimpleNamespace

import pytest
from eth_account import Account
from fastapi import HTTPException

from app.adapters.monad import monad_contract_adapter
from app.api.routes.membership_payment import activate_free_membership
from app.core.config import settings
from app.core.database import database_service
from app.models.base import utc_now
from app.models.membership import MembershipLevel
from app.models.user import OfficialMembershipPayment, User, UserProfile, UserSession, Wallet
from app.services.auth import hash_session_token
from app.services.identity import AuthenticatedIdentity
from app.services.membership_fee import membership_fee_service
from app.services.membership_payment import ConfirmedChainPayment, official_membership_payment_service


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
        level = await session.get(MembershipLevel, "mild-neuro")
        assert level is not None
        level.rank = 10_000
        user = User(display_name="Pending Member")
        session.add(user)
        await session.flush()
        session.add_all(
            [
                UserProfile(
                    user_id=user.id,
                    fan_token_balance=100,
                    fan_token_lifetime_earned=100,
                    level="新生儿",
                ),
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
    monkeypatch.setattr(settings, "membership_fee_wei", 10**18)
    monkeypatch.setattr(settings, "membership_payment_contract_address", gateway)
    monkeypatch.setattr(settings, "membership_identity_contract_address", Account.create().address)
    monkeypatch.setattr(settings, "identity_minter_private_key", "0x" + "11" * 32)
    monkeypatch.setattr(settings, "pinata_jwt", "test-pinata-jwt")
    monkeypatch.setattr(settings, "chain_writes_enabled", True)

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
    assert verify_response.json()["identity_nft_status"] == "READY"

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


async def test_membership_status_does_not_offer_payment_without_gateway(client, monkeypatch):
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

    monkeypatch.setattr(settings, "membership_payment_contract_address", "")
    response = client.get(
        "/api/v1/membership/me",
        headers={"Authorization": f"Bearer {raw_token}"},
    )
    assert response.status_code == 200
    assert response.json()["payment_contract_address"] is None


async def test_zero_fee_membership_activates_without_chain_payment(client, monkeypatch, capsys):
    account = Account.create()
    raw_token = "free-membership-session-token"

    async with database_service.session() as session:
        user = User(display_name="Free Window Member")
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

    monkeypatch.setattr(settings, "membership_fee_wei", 0)
    monkeypatch.setattr(settings, "membership_payment_contract_address", Account.create().address)
    monkeypatch.setattr(settings, "membership_treasury_manager_private_key", "0x" + "22" * 32)
    monkeypatch.setattr(settings, "chain_writes_enabled", True)
    monkeypatch.setattr(settings, "membership_identity_contract_address", "")
    monkeypatch.setattr(settings, "pinata_jwt", "")

    async def current_fee() -> int:
        return 0

    relayed_users: list[str] = []

    async def relay_free_membership(wallet: str, payment_id: str):
        relayed_users.append(wallet)
        return SimpleNamespace(
            transaction_hash="0x" + "ef" * 32,
            block_number=456,
            event_args={"treasury": Account.create().address, "paymentId": payment_id},
        )

    monkeypatch.setattr(monad_contract_adapter, "membership_fee", current_fee)
    monkeypatch.setattr(monad_contract_adapter, "activate_free_membership", relay_free_membership)
    headers = {"Authorization": f"Bearer {raw_token}"}

    status_response = client.get("/api/v1/membership/me", headers=headers)
    assert status_response.status_code == 200
    assert status_response.json()["fee_wei"] == "0"
    assert status_response.json()["payment_id"] is not None

    async def fail_live_fee_lookup() -> int:
        raise AssertionError("activate-free must not query the membership fee from the chain")

    monkeypatch.setattr(membership_fee_service, "get_live_fee", fail_live_fee_lookup)

    activation_response = client.post("/api/v1/membership/activate-free", headers=headers)
    assert activation_response.status_code == 200
    assert activation_response.json()["is_official_member"] is True
    assert activation_response.json()["transaction_hash"] == "0x" + "ef" * 32
    assert relayed_users == [account.address]
    timing_output = capsys.readouterr().out
    assert "step=profile_load" in timing_output
    assert "step=onchain_activation" in timing_output
    assert "step=db_commit" in timing_output
    assert "step=total" in timing_output

    repeated_response = client.post("/api/v1/membership/activate-free", headers=headers)
    assert repeated_response.status_code == 200
    assert repeated_response.json()["transaction_hash"] == activation_response.json()["transaction_hash"]
    assert relayed_users == [account.address]


async def test_free_activation_rejects_nonzero_local_fee_without_chain_lookup(monkeypatch):
    monkeypatch.setattr(settings, "membership_fee_wei", 10**18)

    async def fail_live_fee_lookup() -> int:
        raise AssertionError("activate-free must not query the membership fee from the chain")

    monkeypatch.setattr(membership_fee_service, "get_live_fee", fail_live_fee_lookup)
    identity = AuthenticatedIdentity(
        user_id="non-free-member",
        primary_wallet=Account.create().address,
        wallet_type="external",
        provider="rainbowkit",
    )

    with pytest.raises(HTTPException, match="Official membership is not free right now") as error:
        await activate_free_membership(identity, None)  # type: ignore[arg-type]

    assert error.value.status_code == 409
